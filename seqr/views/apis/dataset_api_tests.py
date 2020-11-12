import json
import mock
import subprocess
from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse
from io import StringIO

from seqr.models import Sample
from seqr.views.apis.dataset_api import add_variants_dataset_handler, receive_igv_table_handler, update_individual_igv_sample
from seqr.views.utils.test_utils import urllib3_responses, AuthenticationTestCase, AnvilAuthenticationTestCase,\
    MixAuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'
INDEX_NAME = 'test_index'
SV_INDEX_NAME = 'test_new_sv_index'
ADD_DATASET_PAYLOAD = json.dumps({'elasticsearchIndex': INDEX_NAME, 'datasetType': 'VARIANTS'})


class DatasetAPITest(object):

    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis', mock.MagicMock())
    @mock.patch('seqr.views.utils.dataset_utils.random.randint')
    @mock.patch('seqr.utils.file_utils.open')
    @urllib3_responses.activate
    def test_add_variants_dataset(self, mock_open, mock_random):
        mock_file_iter = mock_open.return_value.__enter__.return_value.__iter__

        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

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

        urllib3_responses.add_json('/{}/_mapping'.format(INDEX_NAME), {INDEX_NAME: {'mappings': {}}})
        urllib3_responses.add_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': []}}
        }, method=urllib3_responses.POST)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['request must contain fields: elasticsearchIndex, datasetType']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME, 'datasetType': 'NOT_A_TYPE'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid dataset type "NOT_A_TYPE"']})

        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['No samples found in the index. Make sure the specified caller type is correct']})

        self.assertEqual(len(urllib3_responses.calls), 2)
        self.assertDictEqual(
            urllib3_responses.call_request_json(),
            {'aggs': {'sample_ids': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}}}}
        )

        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {
            'aggregations': {'sample_ids': {'buckets': [{'key': 'NA19679'}, {'key': 'NA19678_1'}]}}
        }, method=urllib3_responses.POST)
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index metadata must contain fields: genomeVersion, sampleType, sourceFilePath']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'NOT_A_TYPE',
                'genomeVersion': '37',
                'sourceFilePath': 'invalidpath.txt',
            }}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Sample type not supported: NOT_A_TYPE']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '38',
                'sourceFilePath': 'invalidpath.txt',
            }}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has genome version 38 but this project uses version 37']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'invalidpath.txt',
            }}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Variant call dataset path must end with .vcf.gz or .vds or .bed']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
                'datasetType': 'SV',
            }}}})
        response = self.client.post(url, content_type='application/json', data=ADD_DATASET_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has dataset type SV but expects VARIANTS']})

        urllib3_responses.replace_json('/{}/_mapping'.format(INDEX_NAME), {
            INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.vds',
            }}}})
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

        mock_file_iter.return_value = StringIO('NA19678_1,NA19678,metadata\n')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 2 columns: NA19678_1, NA19678, metadata']})

        # Send valid request
        urllib3_responses.replace_json('/{}/_search?size=0'.format(INDEX_NAME), {'aggregations': {
            'sample_ids': {'buckets': [{'key': 'NA19675'}, {'key': 'NA19679'}, {'key': 'NA19678_1'}]}
        }}, method=urllib3_responses.POST)
        mock_file_iter.return_value = StringIO('NA19678_1,NA19678\n')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
            'datasetType': 'VARIANTS',
        }))
        self.assertEqual(response.status_code, 200)
        mock_open.assert_called_with('mapping.csv', 'r')

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

        # Adding an SV index works additively with the regular variants index
        mock_random.return_value = 1234567
        urllib3_responses.add_json('/{}/_mapping'.format(SV_INDEX_NAME), {
            SV_INDEX_NAME: {'mappings': {'_meta': {
                'sampleType': 'WES',
                'genomeVersion': '37',
                'sourceFilePath': 'test_data.bed',
                'datasetType': 'SV',
            }}}})
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

    def test_receive_alignment_table_handler(self):
        url = reverse(receive_igv_table_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # Send invalid requests
        f = SimpleUploadedFile('samples.csv', b"NA19675\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 2 columns: NA19675']})

        f = SimpleUploadedFile('samples.csv', b"NA19675, /readviz/NA19675.cram\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following Individual IDs do not exist: NA19675']})

        # Send valid request
        f = SimpleUploadedFile('samples.csv', b"NA19675_1,/readviz/NA19675.cram\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 200)

        self.assertDictEqual(response.json(), {
            'uploadedFileId': mock.ANY,
            'errors': [],
            'info': ['Parsed 2 rows from samples.csv', 'No change detected for 1 individuals'],
            'updatesByIndividualGuid': {
                'I000003_na19679': 'gs://readviz/NA19679.bam',
            },
        })

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    def test_add_alignment_sample(self, mock_local_file_exists, mock_subprocess):
        url = reverse(update_individual_igv_sample, args=['I000001_na19675'])
        self.check_manager_login(url)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'request must contain fields: filePath')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': 'invalid_path.txt',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'BAM / CRAM file "invalid_path.txt" must have a .bam or .cram extension')

        mock_local_file_exists.return_value = False
        mock_subprocess.return_value.wait.return_value = 1
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Error accessing "/readviz/NA19675_new.cram"')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': 'gs://readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Error accessing "gs://readviz/NA19675_new.cram"')

        # Send valid request
        mock_local_file_exists.return_value = True
        mock_subprocess.return_value.wait.return_value = 0
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'igvSamplesByGuid': {'S000145_na19675': {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000001_na19675', 'sampleGuid': 'S000145_na19675',
            'filePath': '/readviz/NA19675_new.cram'}}})
        mock_local_file_exists.assert_called_with('/readviz/NA19675_new.cram')

        new_sample_url = reverse(update_individual_igv_sample, args=['I000003_na19679'])
        response = self.client.post(new_sample_url, content_type='application/json', data=json.dumps({
            'filePath': 'gs://readviz/NA19679.bam',
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'igvSamplesByGuid', 'individualsByGuid'})
        self.assertEqual(len(response_json['igvSamplesByGuid']), 1)
        sample_guid = next(iter(response_json['igvSamplesByGuid']))
        self.assertDictEqual(response_json['igvSamplesByGuid'][sample_guid], {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000003_na19679', 'sampleGuid': sample_guid,
            'filePath': 'gs://readviz/NA19679.bam'})
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000003_na19679'])
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000003_na19679']['igvSampleGuids']),
            {sample_guid}
        )
        mock_subprocess.assert_called_with('gsutil ls gs://readviz/NA19679.bam', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)


# Tests for AnVIL access disabled
class LocalDatasetAPITest(AuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', '1kg_project']


def assert_no_list_ws_has_acl(self, acl_call_count):
    self.mock_list_workspaces.assert_not_called()
    self.mock_service_account.get.assert_called_with(
        'api/workspaces/my-seqr-billing/anvil-1kg project n\u00e5me with uni\u00e7\u00f8de/acl')
    self.assertEqual(self.mock_service_account.get.call_count, acl_call_count)


# Test for permissions from AnVIL only
class AnvilDatasetAPITest(AnvilAuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']

    def test_add_variants_dataset(self):
        super(AnvilDatasetAPITest, self).test_add_variants_dataset()
        assert_no_list_ws_has_acl(self, 15)

    def test_receive_alignment_table_handler(self):
        super(AnvilDatasetAPITest, self).test_receive_alignment_table_handler()
        assert_no_list_ws_has_acl(self, 4)

    def test_add_alignment_sample(self):
        super(AnvilDatasetAPITest, self).test_add_alignment_sample()
        assert_no_list_ws_has_acl(self, 7)


# Test for permissions from AnVIL and local
class MixDatasetAPITest(MixAuthenticationTestCase, DatasetAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']

    def test_add_variants_dataset(self):
        super(MixDatasetAPITest, self).test_add_variants_dataset()
        assert_no_list_ws_has_acl(self, 1)

    def test_receive_alignment_table_handler(self):
        super(MixDatasetAPITest, self).test_receive_alignment_table_handler()
        assert_no_list_ws_has_acl(self, 1)

    def test_add_alignment_sample(self):
        super(MixDatasetAPITest, self).test_add_alignment_sample()
        assert_no_list_ws_has_acl(self, 1)
