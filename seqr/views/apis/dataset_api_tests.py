import json
import mock
from copy import deepcopy
from datetime import datetime
from django.urls.base import reverse
from io import StringIO

from seqr.models import Sample, Family
from seqr.views.apis.dataset_api import add_variants_dataset_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses

SEQR_URL = 'https://seqr.broadinstitute.org'
PROJECT_GUID = 'R0001_1kg'
NON_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'
INDEX_NAME = 'test_index'
SV_INDEX_NAME = 'test_new_sv_index'
NEW_SAMPLE_TYPE_INDEX_NAME = 'test_new_index'
ADD_DATASET_PAYLOAD = json.dumps({'elasticsearchIndex': INDEX_NAME, 'datasetType': 'SNV_INDEL'})
MAPPING_PROPS_SAMPLES_NUM_ALT_1 = {
    "samples_num_alt_1": {"type": "keyword"},
}
MAPPING_PROPS_WITH_SAMPLES = {
    "samples": {"type": "keyword"},
}
MAPPING_JSON = {
    INDEX_NAME: {
        'mappings': {
            '_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
            },
            "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1
        }}}
MAPPING_JSON_38 = deepcopy(MAPPING_JSON)
MAPPING_JSON_38[INDEX_NAME]['mappings']['_meta']['genomeVersion'] = '38'

MOCK_REDIS = mock.MagicMock()
MOCK_OPEN = mock.MagicMock()
MOCK_FILE_ITER = MOCK_OPEN.return_value.__enter__.return_value.__iter__


@mock.patch('seqr.utils.redis_utils.redis.StrictRedis', lambda **kwargs: MOCK_REDIS)
@mock.patch('seqr.utils.file_utils.open', MOCK_OPEN)
class DatasetAPITest(object):

    @mock.patch('seqr.models.random.randint')
    @mock.patch('seqr.utils.communication_utils.send_html_email')
    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://seqr.broadinstitute.org/')
    @urllib3_responses.activate
    def test_add_variants_dataset(self, mock_send_email, mock_random):
        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        self.check_data_manager_login(url)

        # Confirm test DB is as expected
        existing_index_sample = Sample.objects.get(sample_id='NA19675')
        self.assertEqual(existing_index_sample.elasticsearch_index, INDEX_NAME)
        self.assertTrue(existing_index_sample.is_active)
        existing_index_sample_guid = existing_index_sample.guid
        existing_old_index_sample = Sample.objects.get(guid='S000130_na19678')
        self.assertNotEqual(existing_old_index_sample.elasticsearch_index, INDEX_NAME)
        self.assertTrue(existing_old_index_sample.is_active)
        existing_old_index_sample_guid = existing_old_index_sample.guid
        existing_sample = Sample.objects.get(sample_id='NA19679')
        self.assertEqual(existing_sample.elasticsearch_index, INDEX_NAME)
        self.assertFalse(existing_sample.is_active)
        existing_sample_guid = existing_sample.guid
        self.assertEqual(Sample.objects.filter(sample_id='NA19678_1').count(), 0)
        self.assertEqual(Sample.objects.filter(sample_id='NA20878').count(), 0)

        mock_random.return_value = 98765432101234567890

        urllib3_responses.add_json('/{}/_mapping'.format(INDEX_NAME), MAPPING_JSON)
        urllib3_responses.add_json('/{}/_search?size=0'.format(INDEX_NAME), {'aggregations': {
            'sample_ids': {'buckets': [{'key': 'NA19675'}, {'key': 'NA19679'}, {'key': 'NA19678_1'}, {'key': 'NA20878'}]}
        }}, method=urllib3_responses.POST)
        MOCK_FILE_ITER.return_value = StringIO('NA19678_1,NA19678\n')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'SNV_INDEL',
        }))
        self.assertEqual(response.status_code, 200)
        MOCK_OPEN.assert_called_with('mapping.csv', 'r')
        MOCK_REDIS.get.assert_called_with('index_metadata__test_index')
        MOCK_REDIS.set.assert_called_with('index_metadata__test_index', '{"test_index": {"sampleType": "WES", "genomeVersion": "37", "sourceFilePath": "test_data.vcf", "fields": {"samples_num_alt_1": "keyword"}}}')

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})

        new_sample_guid = 'S98765432101234567890_na20878'
        replaced_sample_guid = 'S98765432101234567890_na19678_'
        self.assertSetEqual(
            set(response_json['samplesByGuid'].keys()),
            {existing_sample_guid, existing_old_index_sample_guid, replaced_sample_guid, new_sample_guid}
        )
        self.assertDictEqual(response_json['individualsByGuid'], {
            'I000002_na19678': {'sampleGuids': mock.ANY},
            'I000003_na19679': {'sampleGuids': mock.ANY},
            'I000013_na20878': {'sampleGuids': [new_sample_guid]},
        })
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000002_na19678']['sampleGuids']),
            {replaced_sample_guid, existing_old_index_sample_guid}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000003_na19679']['sampleGuids']),
            {existing_sample_guid}
        )

        self.assertDictEqual(response_json['familiesByGuid'], {
            'F000001_1': {'analysisStatus': 'I'},
            'F000009_9': {'analysisStatus': 'I'},
        })
        updated_family = Family.objects.get(guid='F000001_1')
        self.assertEqual(updated_family.analysis_status, 'I')
        self.assertIsNone(updated_family.analysis_status_last_modified_date)
        self.assertIsNone(updated_family.analysis_status_last_modified_by)

        updated_samples = [sample for sample_guid, sample in response_json['samplesByGuid'].items() if sample_guid != existing_old_index_sample_guid]
        self.assertSetEqual(
            {'WES'},
            {sample['sampleType'] for sample in updated_samples}
        )
        self.assertSetEqual(
            {True},
            {sample['isActive'] for sample in updated_samples}
        )
        self.assertSetEqual(
            {datetime.now().strftime('%Y-%m-%d')},
            {sample['loadedDate'][:10] for sample in updated_samples}
        )
        self.assertDictEqual(response_json['samplesByGuid'][existing_old_index_sample_guid], {'isActive': False})

        updated_sample_models = Sample.objects.filter(guid__in=[sample['sampleGuid'] for sample in updated_samples])
        self.assertEqual(len(updated_sample_models), 3)
        self.assertSetEqual({INDEX_NAME}, {sample.elasticsearch_index for sample in updated_sample_models})

        existing_index_sample_model = Sample.objects.get(guid=existing_index_sample_guid)
        self.assertEqual(existing_index_sample_model.sample_type, 'WES')
        self.assertTrue(existing_index_sample_model.is_active)
        self.assertTrue(str(existing_index_sample_model.loaded_date).startswith('2017-02-05'))

        self._assert_expected_notification(mock_send_email, sample_type='WES', count=2)

        # Adding an SV index works additively with the regular variants index
        mock_random.return_value = 1234567
        mock_send_email.reset_mock()
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
        sv_sample_guid = 'S0001234567_na19675_1'
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertListEqual(list(response_json['samplesByGuid'].keys()), [sv_sample_guid])
        self.assertEqual(response_json['samplesByGuid'][sv_sample_guid]['datasetType'], 'SV')
        self.assertEqual(response_json['samplesByGuid'][sv_sample_guid]['sampleType'], 'WES')
        self.assertTrue(response_json['samplesByGuid'][sv_sample_guid]['isActive'])
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertListEqual(list(response_json['individualsByGuid']['I000001_na19675'].keys()), ['sampleGuids'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675']['sampleGuids']),
                            {sv_sample_guid, existing_index_sample_guid})

        # Regular variant sample should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 2)
        self.assertSetEqual({sv_sample_guid, existing_index_sample_guid},
                            {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})

        self._assert_expected_notification(mock_send_email, sample_type='WES SV', count=1)

        # Adding an index for a different sample type works additively
        mock_random.return_value = 987654
        mock_send_email.reset_mock()
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
        new_sample_type_sample_guid = 'S0000987654_na19675_1'
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertListEqual(list(response_json['samplesByGuid'].keys()), [new_sample_type_sample_guid])
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['datasetType'], 'SNV_INDEL')
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['sampleType'], 'WGS')
        self.assertTrue(response_json['samplesByGuid'][new_sample_type_sample_guid]['isActive'])
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertListEqual(list(response_json['individualsByGuid']['I000001_na19675'].keys()), ['sampleGuids'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675']['sampleGuids']),
                            {sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid})

        self._assert_expected_notification(mock_send_email, sample_type='WGS', count=1)

        # Previous variant samples should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 3)
        self.assertSetEqual(
            {sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid},
            {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})

        # Test sending email for adding dataset to a non-analyst project
        url = reverse(add_variants_dataset_handler, args=[NON_ANALYST_PROJECT_GUID])

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), MAPPING_JSON_38)
        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {'aggregations': {
            'sample_ids': {'buckets': [{'key': 'NA21234'}]}
        }}, method=urllib3_responses.POST)

        self.reset_logs()
        mock_send_email.reset_mock()
        mock_send_email.side_effect = Exception('Email server is not configured')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'SNV_INDEL',
        }))
        self.assertEqual(response.status_code, 200)

        self._assert_expected_notification(
            mock_send_email, sample_type='WES', count=1, project_guid=NON_ANALYST_PROJECT_GUID,
            project_name='Non-Analyst Project', recipient='test_user_collaborator@test.com',
        )
        self.assert_json_logs(user=None, offset=6, expected=[(
            'Error sending project email for R0004_non_analyst_project: Email server is not configured', {'detail': {
                'email_body': mock.ANY,
                'subject': 'New data available in seqr', 'to': ['test_user_collaborator@test.com'],
            },
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
                'severity': 'ERROR',
            })
        ])

    def _assert_expected_notification(self, mock_send_email, sample_type, count, email_content=None,
                                      project_guid=PROJECT_GUID, project_name='1kg project nåme with uniçøde',
                                      recipient='test_user_manager@test.com'):
        if not email_content:
            email_content = f'This is to notify you that data for {count} new {sample_type} samples has been loaded in seqr project <a href={SEQR_URL}/project/{project_guid}/project_page>{project_name}</a>'
        mock_send_email.assert_called_once_with(
            email_body=f'Dear seqr user,\n\n{email_content}\n\nAll the best,\nThe seqr team',
            subject='New data available in seqr', to=[recipient], process_message=mock.ANY,
        )

    @urllib3_responses.activate
    def test_add_variants_dataset_errors(self):
        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        self.check_data_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid dataset type "None"']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME, 'datasetType': 'NOT_A_TYPE'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid dataset type "NOT_A_TYPE"']})

        self._assert_expected_add_dataset_errors(url)

    def _assert_expected_add_dataset_errors(self, url):
        response = self.client.post(url, content_type='application/json', data=json.dumps({'datasetType': 'SV'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['request must contain field: "elasticsearchIndex"']})

        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'], 'test_index - Error accessing index: Connection refused: GET /test_index/_mapping')

        urllib3_responses.add_json('/{}/_mapping'.format(INDEX_NAME),
                                   {INDEX_NAME: {'mappings': {"properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['Index metadata must contain fields: genomeVersion, sampleType, sourceFilePath']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'NOT_A_TYPE',
                'genomeVersion': '37',
                'sourceFilePath': 'invalidpath.txt',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Sample type not supported: NOT_A_TYPE']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '38',
                'sourceFilePath': 'invalidpath.txt',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has genome version 38 but this project uses version 37']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'invalidpath.txt',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Variant call dataset path must end with .vcf or .vcf.gz or .bgz or .bed or .mt']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
                'datasetType': 'SV',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has dataset type SV but expects SNV_INDEL']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}},
        })
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Found mismatched sample fields for indices in alias']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vcf',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}},
        })
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Found mismatched sample types for indices in alias']})

        urllib3_responses.add_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': []}}
        }, method=urllib3_responses.POST)
        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), MAPPING_JSON)
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['No samples found. Make sure the specified caller type is correct']})

        self.assertDictEqual(
            urllib3_responses.call_request_json(),
            {'aggs': {'sample_ids': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}}}}
        )

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19679'}, {'key': 'NA19678_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Matches not found for sample ids: NA19678_1. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'SNV_INDEL',
            'ignoreExtraSamplesInCallset': True,
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following families are included in the callset but are missing some family members: 1 (NA19675_1, NA19678).']})

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19673'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'SNV_INDEL',
            'ignoreExtraSamplesInCallset': True,
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': [
            'None of the individuals or samples in the project matched the 1 expected sample id(s)']})

        MOCK_FILE_ITER.return_value = StringIO('NA19678_1,NA19678,metadata\n')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'SNV_INDEL',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 2 columns: NA19678_1, NA19678, metadata']})

        MOCK_FILE_ITER.side_effect = Exception('Unhandled base exception')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'SNV_INDEL',
        }))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'Unhandled base exception')
        MOCK_FILE_ITER.side_effect = None


# Tests for AnVIL access disabled
class LocalDatasetAPITest(AuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', '1kg_project']


def assert_no_anvil_calls(self):
    self.mock_list_workspaces.assert_not_called()
    self.mock_get_ws_access_level.assert_not_called()
    self.assert_no_extra_anvil_calls()


# Test for permissions from AnVIL only
class AnvilDatasetAPITest(AnvilAuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']

    def _assert_expected_add_dataset_errors(self, url):
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors'][0], 'Adding samples is disabled for the hail backend')

    def test_add_variants_dataset(self, *args):
        # Adding dataset is always disabled when ES is disabled, which is tested in test_add_variants_dataset_errors
        pass
