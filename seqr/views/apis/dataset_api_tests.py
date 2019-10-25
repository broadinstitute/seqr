import json
import mock
from datetime import datetime
from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import Sample, Project
from seqr.views.apis.dataset_api import add_variants_dataset_handler, add_alignment_dataset_handler
from seqr.views.utils.test_utils import _check_login


PROJECT_GUID = 'R0001_1kg'
INDEX_NAME = 'test_index'


class DatasetAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.dataset_api.update_xbrowse_vcfffiles', lambda *args: args)
    @mock.patch('seqr.views.utils.dataset_utils.file_iter')
    @mock.patch('seqr.views.utils.dataset_utils.get_index_metadata')
    @mock.patch('seqr.views.utils.dataset_utils.elasticsearch_dsl.Search')
    def test_add_variants_dataset(self, mock_es_search, mock_get_index_metadata, mock_file_iter):
        url = reverse(add_variants_dataset_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # Confirm test DB is as expected
        self.assertFalse(Project.objects.get(guid=PROJECT_GUID).has_new_search)
        existing_index_sample = Sample.objects.get(sample_id='NA19675')
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

        new_sample = Sample.objects.get(sample_id='NA19678_1')
        self.assertSetEqual(
            set(response_json['samplesByGuid'].keys()),
            {existing_index_sample_guid, existing_sample_guid, existing_old_index_sample_guid, new_sample.guid}
        )
        self.assertDictEqual(response_json['individualsByGuid'], {
            'I000001_na19675': {'sampleGuids': [existing_index_sample_guid]},
            'I000002_na19678': {'sampleGuids': [new_sample.guid, existing_old_index_sample_guid]},
            'I000003_na19679': {'sampleGuids': [existing_sample_guid]},
        })
        self.assertDictEqual(response_json['familiesByGuid'], {'F000001_1': {'analysisStatus': 'I'}})
        updated_samples = [sample for sample_guid, sample in response_json['samplesByGuid'].items() if sample_guid != existing_old_index_sample_guid]
        self.assertSetEqual(
            {INDEX_NAME},
            {sample['elasticsearchIndex'] for sample in updated_samples}
        )
        self.assertSetEqual(
            {'test_data.vds'},
            {sample['datasetFilePath'] for sample in
             [response_json['samplesByGuid'][existing_sample_guid], response_json['samplesByGuid'][new_sample.guid]]}
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
        self.assertTrue(response_json['samplesByGuid'][new_sample.guid]['loadedDate'].startswith(today))

        self.assertTrue(Project.objects.get(guid=PROJECT_GUID).has_new_search)

    @mock.patch('seqr.views.utils.dataset_utils.does_google_bucket_file_exist')
    @mock.patch('seqr.views.utils.dataset_utils.proxy_to_igv')
    @mock.patch('seqr.views.utils.dataset_utils.load_uploaded_file')
    def test_add_alignment_dataset(self, mock_load_file_utils, mock_igv_proxy, mock_google_bucket_proxy):
        url = reverse(add_alignment_dataset_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['request must contain fields: sampleType, mappingFile']})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'NOT_A_TYPE',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Sample type not supported: NOT_A_TYPE']})

        mock_load_file_utils.return_value = [('NA19675', 'invalid_path.txt'), ('NA19679', '/readviz/NA19679.bam')]
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['BAM / CRAM file "invalid_path.txt" must have a .bam or .cram extension']})

        mock_load_file_utils.return_value = [('NA19675', '/readviz/NA19675.cram'), ('NA19679', 'gs://readviz/NA19679.bam')]
        mock_igv_proxy.return_value.content = 'Read error'
        mock_igv_proxy.return_value.status_code = 400
        mock_google_bucket_proxy.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Error accessing "/readviz/NA19675.cram": Read error']})

        mock_igv_proxy.return_value.status_code = 200
        mock_igv_proxy.return_value.get.side_effect = lambda key: 'application/octet-stream' if key == 'Content-Type' else 'gzip'
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Error accessing "gs://readviz/NA19679.bam"']})

        mock_google_bucket_proxy.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following Individual IDs do not exist: NA19675']})

        # Send valid request
        mock_load_file_utils.return_value = [('NA19675_1', '/readviz/NA19675.cram'), ('NA19679', 'gs://readviz/NA19679.bam')]
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'sampleType': 'WES',
            'mappingFile': {'uploadedFileId': 1234},
        }))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            {sample['sampleId'] for sample in response_json['samplesByGuid'].values()},
            {'NA19675', 'NA19679'}
        )
        self.assertSetEqual(
            {True},
            {sample['isActive'] for sample in response_json['samplesByGuid'].values()}
        )
        self.assertSetEqual(
            {'WES'},
            {sample['sampleType'] for sample in response_json['samplesByGuid'].values()}
        )

        sample_guid_na19675 = next(guid for guid, sample in response_json['samplesByGuid'].items() if sample['sampleId'] == 'NA19675')
        sample_guid_na19679 = next(guid for guid, sample in response_json['samplesByGuid'].items() if sample['sampleId'] == 'NA19679')
        self.assertEqual(response_json['samplesByGuid'][sample_guid_na19675]['datasetFilePath'], '/readviz/NA19675.cram')
        self.assertEqual(response_json['samplesByGuid'][sample_guid_na19679]['datasetFilePath'], 'gs://readviz/NA19679.bam')

        self.assertSetEqual( set(response_json['individualsByGuid'].keys()), {'I000001_na19675', 'I000003_na19679'})
        self.assertTrue(sample_guid_na19675 in response_json['individualsByGuid']['I000001_na19675']['sampleGuids'])
        self.assertTrue(sample_guid_na19679 in response_json['individualsByGuid']['I000003_na19679']['sampleGuids'])
