import json
import mock
from datetime import datetime
from django.urls.base import reverse
from io import StringIO

from seqr.models import Sample
from seqr.views.apis.dataset_api import add_variants_dataset_handler
from seqr.views.utils.test_utils import urllib3_responses, AuthenticationTestCase, AnvilAuthenticationTestCase,\
    MixAuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'
NON_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'
INDEX_NAME = 'test_index'
SV_INDEX_NAME = 'test_new_sv_index'
NEW_SAMPLE_TYPE_INDEX_NAME = 'test_new_index'
ADD_DATASET_PAYLOAD = json.dumps({'elasticsearchIndex': INDEX_NAME, 'datasetType': 'VARIANTS'})
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
                'sourceFilePath': 'test_data.vds',
            },
            "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1
        }}}


MOCK_REDIS = mock.MagicMock()
MOCK_OPEN = mock.MagicMock()
MOCK_FILE_ITER = MOCK_OPEN.return_value.__enter__.return_value.__iter__

@mock.patch('seqr.utils.redis_utils.redis.StrictRedis', lambda **kwargs: MOCK_REDIS)
@mock.patch('seqr.utils.file_utils.open', MOCK_OPEN)
class DatasetAPITest(object):

    @mock.patch('seqr.views.utils.dataset_utils.random.randint')
    @mock.patch('seqr.views.apis.dataset_api.safe_post_to_slack')
    @mock.patch('seqr.views.apis.dataset_api.send_html_email')
    @mock.patch('seqr.views.apis.dataset_api.BASE_URL', 'https://seqr.broadinstitute.org/')
    @mock.patch('seqr.views.apis.dataset_api.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @urllib3_responses.activate
    def test_add_variants_dataset(self, mock_send_email, mock_send_slack, mock_random):
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

        mock_random.return_value = 98765432101234567890

        urllib3_responses.add_json('/{}/_mapping'.format(INDEX_NAME), MAPPING_JSON)
        urllib3_responses.add_json('/{}/_search?size=0'.format(INDEX_NAME), {'aggregations': {
            'sample_ids': {'buckets': [{'key': 'NA19675'}, {'key': 'NA19679'}, {'key': 'NA19678_1'}]}
        }}, method=urllib3_responses.POST)
        MOCK_FILE_ITER.return_value = StringIO('NA19678_1,NA19678\n')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 200)
        MOCK_OPEN.assert_called_with('mapping.csv', 'r')
        MOCK_REDIS.get.assert_called_with('index_metadata__test_index')
        MOCK_REDIS.set.assert_called_with('index_metadata__test_index', '{"test_index": {"sampleType": "WES", "genomeVersion": "37", "sourceFilePath": "test_data.vds", "fields": {"samples_num_alt_1": "keyword"}}}')

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})

        new_sample_guid = 'S98765432101234567890_NA19678_'
        self.assertSetEqual(
            set(response_json['samplesByGuid'].keys()),
            {existing_index_sample_guid, existing_sample_guid, existing_old_index_sample_guid, new_sample_guid}
        )
        self.assertDictEqual(response_json['individualsByGuid'], {
            'I000001_na19675': {'sampleGuids': [existing_index_sample_guid]},
            'I000002_na19678': {'sampleGuids': mock.ANY},
            'I000003_na19679': {'sampleGuids': [existing_sample_guid]},
        })
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000002_na19678']['sampleGuids']),
            {new_sample_guid, existing_old_index_sample_guid}
        )
        self.assertDictEqual(response_json['familiesByGuid'], {'F000001_1': {'analysisStatus': 'I'}})
        updated_samples = [sample for sample_guid, sample in response_json['samplesByGuid'].items() if sample_guid != existing_old_index_sample_guid]
        self.assertSetEqual(
            {'WES'},
            {sample['sampleType'] for sample in updated_samples}
        )
        self.assertSetEqual(
            {True},
            {sample['isActive'] for sample in updated_samples}
        )
        self.assertDictEqual(response_json['samplesByGuid'][existing_old_index_sample_guid], {'isActive': False})

        # Only the new/updated samples should have an updated loaded date
        self.assertTrue(response_json['samplesByGuid'][existing_index_sample_guid]['loadedDate'].startswith('2017-02-05'))
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertTrue(response_json['samplesByGuid'][existing_sample_guid]['loadedDate'].startswith(today))
        self.assertTrue(response_json['samplesByGuid'][new_sample_guid]['loadedDate'].startswith(today))

        updated_sample_models = Sample.objects.filter(guid__in=[sample['sampleGuid'] for sample in updated_samples])
        self.assertEqual(len(updated_sample_models), 3)
        self.assertSetEqual({INDEX_NAME}, {sample.elasticsearch_index for sample in updated_sample_models})

        mock_send_email.assert_not_called()
        mock_send_slack.assert_called_with(
            'seqr-data-loading',
            '1 new samples are loaded in https://seqr.broadinstitute.org/project/{guid}/project_page\n            ```[\'NA19678_1\']```\n            '.format(
                guid=PROJECT_GUID
            ))

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
                            set([sv_sample_guid, existing_index_sample_guid]))

        # Regular variant sample should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 2)
        self.assertSetEqual({sv_sample_guid, existing_index_sample_guid}, {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})

        mock_send_email.assert_not_called()
        mock_send_slack.assert_called_with(
            'seqr-data-loading',
            '1 new samples are loaded in https://seqr.broadinstitute.org/project/{guid}/project_page\n            ```[\'NA19675_1\']```\n            '.format(
                guid=PROJECT_GUID
            ))

        # Adding an index for a different sample type works additively
        mock_random.return_value = 987654
        mock_send_slack.reset_mock()
        urllib3_responses.add_json('/{}/_mapping'.format(NEW_SAMPLE_TYPE_INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data_1.vds',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data_2.vds',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
        })
        urllib3_responses.add_json('/{}/_search?size=0'.format(NEW_SAMPLE_TYPE_INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19675_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': NEW_SAMPLE_TYPE_INDEX_NAME,
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})
        new_sample_type_sample_guid = 'S987654_NA19675_1'
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertListEqual(list(response_json['samplesByGuid'].keys()), [new_sample_type_sample_guid])
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['datasetType'], 'VARIANTS')
        self.assertEqual(response_json['samplesByGuid'][new_sample_type_sample_guid]['sampleType'], 'WGS')
        self.assertTrue(response_json['samplesByGuid'][new_sample_type_sample_guid]['isActive'])
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertListEqual(list(response_json['individualsByGuid']['I000001_na19675'].keys()), ['sampleGuids'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675']['sampleGuids']),
                            set([sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid]))

        mock_send_email.assert_not_called()
        mock_send_slack.assert_called_with(
            'seqr-data-loading',
            '1 new samples are loaded in https://seqr.broadinstitute.org/project/{guid}/project_page\n            ```[\'NA19675_1\']```\n            '.format(
                guid=PROJECT_GUID
            ))

        # Previous variant samples should still be active
        sample_models = Sample.objects.filter(individual__guid='I000001_na19675')
        self.assertEqual(len(sample_models), 3)
        self.assertSetEqual({sv_sample_guid, existing_index_sample_guid, new_sample_type_sample_guid}, {sample.guid for sample in sample_models})
        self.assertSetEqual({True}, {sample.is_active for sample in sample_models})

        # Test sending email for adding dataset to a non-analyst project
        url = reverse(add_variants_dataset_handler, args=[NON_ANALYST_PROJECT_GUID])

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {'aggregations': {
            'sample_ids': {'buckets': [{'key': 'NA21234'}]}
        }}, method=urllib3_responses.POST)

        mock_send_slack.reset_mock()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 200)

        if self.ANVIL_DISABLED:
            mock_send_email.assert_not_called()
        else:
            mock_send_email.assert_called_with("""Hi Test Manager User,
We are following up on your request to load data from AnVIL on March 12, 2017.
We have loaded 1 samples from the AnVIL workspace <a href=https://anvil.terra.bio/#workspaces/my-seqr-billing/anvil-non-analyst-project 1000 Genomes Demo>my-seqr-billing/anvil-non-analyst-project 1000 Genomes Demo</a> to the corresponding seqr project <a href=https://seqr.broadinstitute.org/project/{guid}/project_page>Non-Analyst Project</a>. Let us know if you have any questions.
- The seqr team\n""".format(guid=NON_ANALYST_PROJECT_GUID),
                                               subject='New data available in seqr',
                                               to=['test_user_manager@test.com'])
        mock_send_slack.assert_not_called()

    @urllib3_responses.activate
    def test_add_variants_dataset_errors(self):
        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        self.check_data_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['request must contain fields: elasticsearchIndex, datasetType']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME, 'datasetType': 'NOT_A_TYPE'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid dataset type "NOT_A_TYPE"']})

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
        self.assertDictEqual(response.json(), {'errors': ['Variant call dataset path must end with .vds or .vcf.gz or .bgz or .bed']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
                'datasetType': 'SV',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has dataset type SV but expects VARIANTS']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
            }, "properties": MAPPING_PROPS_SAMPLES_NUM_ALT_1}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}},
        })
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Found mismatched sample fields for indices in alias']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            'sub_index_1': {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
            }, "properties": MAPPING_PROPS_WITH_SAMPLES}},
            'sub_index_2': {'mappings': {'_meta': {
                'sampleType': 'WGS',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
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
            'errors': ['No samples found in the index. Make sure the specified caller type is correct']})

        self.assertDictEqual(
            urllib3_responses.call_request_json(),
            {'aggs': {'sample_ids': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}}}}
        )

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19679'}, {'key': 'NA19678_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Matches not found for ES sample ids: NA19678_1. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'VARIANTS',
            'ignoreExtraSamplesInCallset': True,
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following families are included in the callset but are missing some family members: 1 (NA19675_1, NA19678).']})

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19673'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'datasetType': 'VARIANTS',
            'ignoreExtraSamplesInCallset': True,
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': [
            'None of the individuals or samples in the project matched the 1 expected sample id(s)']})

        MOCK_FILE_ITER.return_value = StringIO('NA19678_1,NA19678,metadata\n')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 2 columns: NA19678_1, NA19678, metadata']})

        MOCK_FILE_ITER.side_effect = Exception('Unhandled base exception')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'Unhandled base exception')
        MOCK_FILE_ITER.side_effect = None


# Tests for AnVIL access disabled
class LocalDatasetAPITest(AuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', '1kg_project']
    ANVIL_DISABLED = True


def assert_no_anvil_calls(self):
    self.mock_list_workspaces.assert_not_called()
    self.mock_get_ws_access_level.assert_not_called()
    self.mock_get_ws_acl.assert_not_called()


# Test for permissions from AnVIL only
class AnvilDatasetAPITest(AnvilAuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']
    ANVIL_DISABLED = False

    def test_add_variants_dataset(self, *args):
        super(AnvilDatasetAPITest, self).test_add_variants_dataset(*args)
        assert_no_anvil_calls(self)


# Test for permissions from AnVIL and local
class MixDatasetAPITest(MixAuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']
    ANVIL_DISABLED = False

    def test_add_variants_dataset(self, *args):
        super(MixDatasetAPITest, self).test_add_variants_dataset(*args)
        assert_no_anvil_calls(self)
