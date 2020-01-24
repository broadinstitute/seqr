import json
import mock
from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import Sample
from seqr.views.apis.dataset_api import add_variants_dataset_handler, receive_alignment_table_handler, update_individual_alignment_sample
from seqr.views.utils.test_utils import _check_login


PROJECT_GUID = 'R0001_1kg'
INDEX_NAME = 'test_index'


class DatasetAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.dataset_utils.random.randint', lambda *args: 98765432101234567890)
    @mock.patch('seqr.views.utils.dataset_utils.file_iter')
    @mock.patch('seqr.views.utils.dataset_utils.get_index_metadata')
    @mock.patch('seqr.views.utils.dataset_utils.elasticsearch_dsl.Search')
    def test_add_variants_dataset(self, mock_es_search, mock_get_index_metadata, mock_file_iter):
        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # Confirm test DB is as expected
        existing_index_sample = Sample.objects.get(sample_id='NA19675', dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
        self.assertEqual(existing_index_sample.elasticsearch_index, INDEX_NAME)
        self.assertNotEqual(existing_index_sample.dataset_file_path, 'test_data.vds')
        self.assertTrue(existing_index_sample.is_active)
        existing_index_sample_guid = existing_index_sample.guid
        existing_old_index_sample = Sample.objects.get(sample_id='NA19678')
        self.assertNotEqual(existing_old_index_sample.elasticsearch_index, INDEX_NAME)
        self.assertTrue(existing_old_index_sample.is_active)
        existing_old_index_sample_guid = existing_old_index_sample.guid
        existing_sample = Sample.objects.get(sample_id='NA19679')
        self.assertEqual(existing_sample.elasticsearch_index, INDEX_NAME)
        self.assertNotEqual(existing_sample.dataset_file_path, 'test_data.vds')
        self.assertFalse(existing_sample.is_active)
        existing_sample_guid = existing_sample.guid
        self.assertEqual(Sample.objects.filter(sample_id='NA19678_1').count(), 0)

        mock_es_search.return_value.params.return_value.execute.return_value.aggregations.sample_ids.buckets = [
            {'key': 'NA19679'}, {'key': 'NA19678_1'},
        ]

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['"elasticsearchIndex" is required']})

        mock_get_index_metadata.return_value = {}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index metadata must contain fields: genomeVersion, sampleType, sourceFilePath']})

        mock_get_index_metadata.return_value = {INDEX_NAME: {
            'sampleType': 'NOT_A_TYPE',
            'genomeVersion': '37',
            'sourceFilePath': 'invalidpath.txt',
        }}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Sample type not supported: NOT_A_TYPE']})

        mock_get_index_metadata.return_value = {INDEX_NAME: {
            'sampleType': 'WES',
            'genomeVersion': '38',
            'sourceFilePath': 'invalidpath.txt',
        }}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Index "test_index" has genome version 38 but this project uses version 37']})

        mock_get_index_metadata.return_value = {INDEX_NAME: {
            'sampleType': 'WES',
            'genomeVersion': '37',
            'sourceFilePath': 'invalidpath.txt',
        }}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Variant call dataset path must end with .vcf.gz or .vds']})

        mock_get_index_metadata.return_value = {INDEX_NAME: {
            'sampleType': 'WES',
            'genomeVersion': '37',
            'sourceFilePath': 'invalidpath.txt',
        }}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Variant call dataset path must end with .vcf.gz or .vds']})

        mock_get_index_metadata.return_value = {INDEX_NAME: {
            'sampleType': 'WES',
            'genomeVersion': '37',
            'sourceFilePath': 'test_data.vds',
        }}
        response = self.client.post(url, content_type='application/json', data=json.dumps({'elasticsearchIndex': INDEX_NAME}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Matches not found for ES sample ids: NA19678_1. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'ignoreExtraSamplesInCallset': True,
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following families are included in the callset but are missing some family members: 1 (NA19678, NA19675_1).']})

        # Send valid request
        mock_es_search.return_value.params.return_value.execute.return_value.aggregations.sample_ids.buckets = [
            {'key': 'NA19675'}, {'key': 'NA19679'}, {'key': 'NA19678_1'},
        ]
        mock_file_iter.return_value = ['NA19678_1,NA19678']
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'elasticsearchIndex': INDEX_NAME,
            'mappingFilePath': 'mapping.csv',
        }))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid', 'familiesByGuid'})

        new_sample_guid = 'S98765432101234567890_NA19678_'
        self.assertSetEqual(
            set(response_json['samplesByGuid'].keys()),
            {existing_index_sample_guid, existing_sample_guid, existing_old_index_sample_guid, new_sample_guid}
        )
        self.assertDictEqual(response_json['individualsByGuid'], {
            'I000001_na19675': {'sampleGuids': [existing_index_sample_guid, 'S000145_na19675']},
            'I000002_na19678': {'sampleGuids': [new_sample_guid, existing_old_index_sample_guid]},
            'I000003_na19679': {'sampleGuids': [existing_sample_guid]},
        })
        self.assertDictEqual(response_json['familiesByGuid'], {'F000001_1': {'analysisStatus': 'I'}})
        updated_samples = [sample for sample_guid, sample in response_json['samplesByGuid'].items() if sample_guid != existing_old_index_sample_guid]
        self.assertSetEqual(
            {'test_data.vds'},
            {sample['datasetFilePath'] for sample in
             [response_json['samplesByGuid'][existing_sample_guid], response_json['samplesByGuid'][new_sample_guid]]}
        )
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

    def test_receive_alignment_table_handler(self):
        url = reverse(receive_alignment_table_handler, args=[PROJECT_GUID])
        _check_login(self, url)

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
            'updatesByIndividualGuid': {'I000003_na19679': 'gs://readviz/NA19679.bam'},
        })

    @mock.patch('seqr.utils.file_utils.does_google_bucket_file_exist')
    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    def test_add_alignment_sample(self, mock_local_file_exists, mock_google_bucket_file_exists):
        url = reverse(update_individual_alignment_sample, args=['I000001_na19675'])
        _check_login(self, url)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'request must contain fields: sampleType, datasetFilePath')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'NOT_A_TYPE',
            'datasetFilePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Sample type not supported: NOT_A_TYPE')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'datasetFilePath': 'invalid_path.txt',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'BAM / CRAM file "invalid_path.txt" must have a .bam or .cram extension')

        mock_local_file_exists.return_value = False
        mock_google_bucket_file_exists.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'datasetFilePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Error accessing "/readviz/NA19675_new.cram"')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'datasetFilePath': 'gs://readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Error accessing "gs://readviz/NA19675_new.cram"')

        # Send valid request
        mock_local_file_exists.return_value = True
        mock_google_bucket_file_exists.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'datasetFilePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'samplesByGuid': {'S000145_na19675': {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000001_na19675', 'sampleGuid': 'S000145_na19675',
            'createdDate': '2017-02-05T06:42:55.397Z', 'sampleType': 'WES', 'sampleId': 'NA19675_new', 'isActive': True,
            'datasetFilePath': '/readviz/NA19675_new.cram', 'loadedDate': '2017-02-05T06:42:55.397Z',
            'datasetType': 'ALIGN'}}})

        new_sample_url = reverse(update_individual_alignment_sample, args=['I000003_na19679'])
        response = self.client.post(new_sample_url, content_type='application/json', data=json.dumps({
            'sampleType': 'WGS',
            'datasetFilePath': 'gs://readviz/NA19679.bam',
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'samplesByGuid', 'individualsByGuid'})
        self.assertEqual(len(response_json['samplesByGuid']), 1)
        sample_guid = response_json['samplesByGuid'].keys()[0]
        self.assertDictEqual(response_json['samplesByGuid'][sample_guid], {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000003_na19679', 'sampleGuid': sample_guid,
            'createdDate': mock.ANY, 'sampleType': 'WGS', 'sampleId': 'NA19679', 'isActive': True,
            'datasetFilePath': 'gs://readviz/NA19679.bam', 'loadedDate': mock.ANY,
            'datasetType': 'ALIGN'})
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertTrue(response_json['samplesByGuid'][sample_guid]['loadedDate'].startswith(today))
        self.assertListEqual(response_json['individualsByGuid'].keys(), ['I000003_na19679'])
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000003_na19679']['sampleGuids']),
            {'S000131_na19679', sample_guid}
        )
