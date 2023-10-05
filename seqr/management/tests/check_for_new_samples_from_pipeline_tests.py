from datetime import datetime
from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError
import json
import mock

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase
from seqr.models import Family, Individual, Sample

SEQR_URL = 'https://seqr.broadinstitute.org/'
PROJECT_GUID = 'R0001_1kg'
EXTERNAL_PROJECT_GUID = 'R0004_non_analyst_project'

# TODO inline
SLACK_MESSAGE_TEMPLATE = f'{{count}} new {{type}} samples are loaded in {SEQR_URL}project/{PROJECT_GUID}/project_page\n```{{samples}}```'

namespace_path = 'ext-data/anvil-non-analyst-project 1000 Genomes Demo'
anvil_link = f'<a href=https://anvil.terra.bio/#workspaces/{namespace_path}>{namespace_path}</a>'
seqr_link = f'<a href=https://seqr.broadinstitute.org/project/{EXTERNAL_PROJECT_GUID}/project_page>Non-Analyst Project</a>'
EMAIL = f"""Hi Test Manager User,
We are following up on your request to load data from AnVIL on March 12, 2017.
We have loaded 1 samples from the AnVIL workspace {anvil_link} to the corresponding seqr project {seqr_link}. Let us know if you have any questions.
- The seqr team\n"""


class CheckNewSamplesTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.dataset_utils.random.randint')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.utils.search.add_data_utils.safe_post_to_slack')
    @mock.patch('seqr.utils.search.add_data_utils.send_html_email')
    @mock.patch('seqr.utils.search.add_data_utils.BASE_URL', SEQR_URL)
    @mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL', 'anvil-data-loading')
    @mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
    def test_command(self, mock_send_email, mock_send_slack, mock_subprocess, mock_random):
        # Test missing required arguments
        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline')
        self.assertEqual(str(ce.exception), 'Error: the following arguments are required: path, version')

        # TODO test errors

        # TODO test logging

        # TODO use side_effect in definition or single return value?
        mock_random.return_value = 98765432101234567890

        # 'sourceFilePath': 'test_data.vcf',
        # 'sample_ids': {'buckets': [{'key': 'NA19675'}, {'key': 'NA19679'}, {'key': 'NA19678_1'}, {'key': 'NA20878'}]}
        # MOCK_FILE_ITER.return_value = StringIO('NA19678_1,NA19678\n')

        version = 'auto__2023-08-08'
        callset = '1kg.vcf.gz'
        mock_subprocess.return_value.stdout = [json.dumps({
            'callset': callset, 'sample_type': 'WES', 'families': {
                'F000011_11': ['NA20885'],
                'F000012_12': ['NA20889'],
                'F000014_14': ['NA21234'],
            },
        }).encode()]

        call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', version)

        mock_subprocess.assert_called_with(
            f'gsutil cat gs://seqr-datasets/v03/GRCh38/SNV_INDEL/runs/{version}/metadata.json',
            stdout=-1, stderr=-2, shell=True)

        # Tests models updated
        # TODO constants
        new_sample_guid = 'S98765432101234567890_NA21234'
        replaced_sample_guid = 'S98765432101234567890_NA20885'
        existing_sample_guid = 'S000154_na20889'
        updated_sample_models = Sample.objects.filter(guid__in={
            existing_sample_guid, replaced_sample_guid, new_sample_guid})
        self.assertEqual(len(updated_sample_models), 3)
        self.assertSetEqual({'WES'}, set(updated_sample_models.values_list('sample_type', flat=True)))
        self.assertSetEqual({'SNV_INDEL'}, set(updated_sample_models.values_list('dataset_type', flat=True)))
        self.assertSetEqual({True}, set(updated_sample_models.values_list('is_active', flat=True)))
        self.assertSetEqual({callset}, set(updated_sample_models.values_list('elasticsearch_index', flat=True)))
        self.assertSetEqual({version}, set(updated_sample_models.values_list('data_source', flat=True)))
        self.assertSetEqual(
            {datetime.now().strftime('%Y-%m-%d')},
            {date.strftime('%Y-%m-%d') for date in updated_sample_models.values_list('loaded_date', flat=True)}
        )

        old_data_sample_guid = 'S000143_na20885'
        self.assertFalse(Sample.objects.get(guid=old_data_sample_guid).is_active)

        self.assertSetEqual(
            set(Individual.objects.get(guid='I000015_na20885').sample_set.values_list('guid', flat=True)),
            {replaced_sample_guid, old_data_sample_guid}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000017_na20889').sample_set.values_list('guid', flat=True)),
            {existing_sample_guid}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000018_na21234').sample_set.values_list('guid', flat=True)),
            {'S000147_na21234', new_sample_guid}
        )

        self.assertListEqual(list(Family.objects.filter(
            guid__in=['F000011_11', 'F000012_12']
        ).values('analysis_status', 'analysis_status_last_modified_date')), [
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
        ])
        self.assertEqual(Family.objects.get(guid='F000014_14').analysis_status, 'Rncc')

        # Test notifications
        self.assertEqual(mock_send_slack.call_count, 2)
        mock_send_slack.assert_has_calls([
            mock.call(
                'seqr-data-loading',
                f'1 new WES samples are loaded in {SEQR_URL}project/R0003_test/project_page\n```NA20889```',
            ),
            mock.call(
                'anvil-data-loading',
                f'1 new WES samples are loaded in {SEQR_URL}project/{EXTERNAL_PROJECT_GUID}/project_page',
            ),
        ])

        self.assertEqual(mock_send_email.call_count, 1)
        mock_send_email.assert_called_with(EMAIL, subject='New data available in seqr', to=['test_user_manager@test.com'])

        # TODO
        # Adding an SV index works additively with the regular variants index
        mock_random.return_value = 1234567
        mock_send_slack.reset_mock()
        urllib3_responses.add_json('/{}/_mapping'.format(SV_INDEX_NAME), {
            SV_INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.bed',
                'datasetType': 'SV',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}}})
        urllib3_responses.add_json('/{}/_search?size=0'.format(SV_INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19675_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': SV_INDEX_NAME,
            'datasetType': 'SV',
        }))
        self.assertEqual(response.status_code, 200)

        self.assertDictEqual(
            urllib3_responses.call_request_json(),
            {'aggs': {'sample_ids': {'terms': {'field': 'samples', 'size': 10000}}}}
        )

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})
        sv_sample_guid = 'S1234567_NA19675_1'
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertListEqual(list(response_json['samplesByGuid'].keys()), [sv_sample_guid])
        self.assertEqual(response_json['samplesByGuid'][sv_sample_guid]['datasetType'], 'SV')
        self.assertEqual(response_json['samplesByGuid'][sv_sample_guid]['sampleType'], 'WES')
        self.assertTrue(response_json['samplesByGuid'][sv_sample_guid]['isActive'])
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertListEqual(list(response_json['individualsByGuid']['I000001_na19675'].keys()), ['sampleGuids'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675']['sampleGuids']),
                            {sv_sample_guid, existing_index_sample_guid} | existing_rna_seq_sample_guids)

        # Regular variant sample should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 4)
        self.assertSetEqual({sv_sample_guid, existing_index_sample_guid} | existing_rna_seq_sample_guids,
                            {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})

        mock_send_email.assert_not_called()
        mock_send_slack.assert_called_with(
            'seqr-data-loading', SLACK_MESSAGE_TEMPLATE.format(type='WES SV', samples='NA19675_1', count=1))

        # Adding an index for a different sample type works additively
        mock_random.return_value = 987654
        mock_send_slack.reset_mock()
        urllib3_responses.add_json('/{}/_mapping'.format(NEW_SAMPLE_TYPE_INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data_1.vcf',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data_2.vcf',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
        })
        urllib3_responses.add_json('/{}/_search?size=0'.format(NEW_SAMPLE_TYPE_INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19675_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': NEW_SAMPLE_TYPE_INDEX_NAME,
            'datasetType': 'SNV_INDEL',
        }))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})
        new_sample_type_sample_guid = 'S987654_NA19675_1'
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertListEqual(list(response_json['samplesByGuid'].keys()), [new_sample_type_sample_guid])
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['datasetType'], 'SNV_INDEL')
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['sampleType'], 'WGS')
        self.assertTrue(response_json['samplesByGuid'][new_sample_type_sample_guid]['isActive'])
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertListEqual(list(response_json['individualsByGuid']['I000001_na19675'].keys()), ['sampleGuids'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675']['sampleGuids']),
                            {sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid} |
                            existing_rna_seq_sample_guids)
        self.assertTrue(new_sample_type_sample_guid not in existing_rna_seq_sample_guids)

        mock_send_email.assert_not_called()
        mock_send_slack.assert_called_with(
            'seqr-data-loading', SLACK_MESSAGE_TEMPLATE.format(type='WGS', samples='NA19675_1', count=1))

        # Previous variant samples should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 5)
        self.assertSetEqual(
            {sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid} | existing_rna_seq_sample_guids,
            {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})
