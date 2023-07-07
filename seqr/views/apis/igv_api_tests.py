import json
import mock
import responses
import subprocess # nosec

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse
from seqr.views.apis.igv_api import fetch_igv_track, receive_igv_table_handler, update_individual_igv_sample, \
    igv_genomes_proxy, receive_bulk_igv_table_handler
from seqr.views.apis.igv_api import GS_STORAGE_ACCESS_CACHE_KEY
from seqr.views.utils.test_utils import AuthenticationTestCase

STREAMING_READS_CONTENT = [b'CRAM\x03\x83', b'\\\t\xfb\xa3\xf7%\x01', b'[\xfc\xc9\t\xae']
PROJECT_GUID = 'R0001_1kg'


@mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
class IgvAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @responses.activate
    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.views.apis.igv_api.safe_redis_get_json')
    @mock.patch('seqr.views.apis.igv_api.safe_redis_set_json')
    def test_proxy_google_to_igv(self, mock_set_redis, mock_get_redis, mock_subprocess, mock_file_logger):
        mock_ls_subprocess = mock.MagicMock()
        mock_access_token_subprocess = mock.MagicMock()
        mock_subprocess.side_effect = [mock_ls_subprocess, mock_access_token_subprocess]
        mock_ls_subprocess.stdout = iter([b'CommandException: One or more URLs matched no objects.'])
        mock_ls_subprocess.wait.return_value = 1
        mock_access_token_subprocess.stdout = iter([b'token1\n', b'token2\n'])
        mock_access_token_subprocess.wait.return_value = 0
        mock_get_redis.return_value = None

        responses.add(responses.GET, 'https://storage.googleapis.com/fc-secure-project_A/sample_1.bai',
                      stream=True,
                      body=b'\n'.join(STREAMING_READS_CONTENT), status=206)
        responses.add(responses.POST, 'https://www.googleapis.com/oauth2/v1/tokeninfo',
                      body=b'{"expires_in": 3599}', status=200)

        url = reverse(fetch_igv_track, args=[PROJECT_GUID, 'gs://fc-secure-project_A/sample_1.bam.bai'])
        self.check_collaborator_login(url)
        response = self.client.get(url, HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(next(response.streaming_content), b'\n'.join(STREAMING_READS_CONTENT))
        self.assertEqual(responses.calls[1].request.headers.get('Range'), 'bytes=100-200')
        self.assertEqual(responses.calls[1].request.headers.get('Authorization'), 'Bearer token1')
        self.assertEqual(responses.calls[1].request.headers.get('x-goog-user-project'), 'anvil-datastorage')
        mock_get_redis.assert_called_with(GS_STORAGE_ACCESS_CACHE_KEY)
        mock_set_redis.assert_called_with(GS_STORAGE_ACCESS_CACHE_KEY, 'token1', expire=3594)
        mock_subprocess.assert_has_calls([
            mock.call('gsutil -u anvil-datastorage ls gs://fc-secure-project_A/sample_1.bam.bai', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True),
            mock.call('gcloud auth print-access-token', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True),
        ])
        mock_ls_subprocess.wait.assert_called_once()
        mock_access_token_subprocess.wait.assert_called_once()
        mock_file_logger.info.assert_any_call(
            'CommandException: One or more URLs matched no objects.', self.collaborator_user)

        mock_get_redis.reset_mock()
        mock_get_redis.return_value = 'token3'
        mock_set_redis.reset_mock()
        mock_subprocess.reset_mock()
        responses.add(responses.GET, 'https://storage.googleapis.com/project_A/sample_1.bed.gz',
                      stream=True,
                      body=b'\n'.join(STREAMING_READS_CONTENT), status=200)
        url = reverse(fetch_igv_track, args=[PROJECT_GUID, 'gs://project_A/sample_1.bed.gz'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(responses.calls[2].request.headers.get('Range'))
        self.assertEqual(responses.calls[2].request.headers.get('Authorization'), 'Bearer token3')
        self.assertIsNone(responses.calls[2].request.headers.get('x-goog-user-project'))
        mock_get_redis.assert_called_with(GS_STORAGE_ACCESS_CACHE_KEY)
        mock_set_redis.assert_not_called()
        mock_subprocess.assert_not_called()

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.utils.file_utils.open')
    def test_proxy_local_to_igv(self, mock_open, mock_subprocess):
        mock_subprocess.return_value.stdout = STREAMING_READS_CONTENT
        mock_open.return_value.__enter__.return_value.__iter__.return_value = STREAMING_READS_CONTENT

        url = reverse(fetch_igv_track, args=[PROJECT_GUID, '/project_A/sample_1.bam.bai'])
        self.check_collaborator_login(url)
        response = self.client.get(url, HTTP_RANGE='bytes=100-250')
        self.assertEqual(response.status_code, 206)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_subprocess.assert_called_with(
            'dd skip=100 count=150 bs=1 if=/project_A/sample_1.bai',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        mock_open.assert_not_called()

        # test no byte range
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_open.assert_called_with('/project_A/sample_1.bai', 'rb')

    def test_receive_alignment_table_handler(self):
        url = reverse(receive_igv_table_handler, args=[PROJECT_GUID])
        self.check_pm_login(url)

        # Send invalid requests
        f = SimpleUploadedFile('samples.csv', b"NA19675\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 2 or 3 columns: NA19675']})

        f = SimpleUploadedFile('samples.csv', b"NA19675, /readviz/NA19675.cram\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['The following Individual IDs do not exist: NA19675']})

        # Send valid request
        f = SimpleUploadedFile('samples.csv', b"NA19675_1,/readviz/NA19675.cram\nNA19675_1,gs://readviz/batch_10.dcr.bed.gz,NA19675\nNA19679,gs://readviz/NA19679.bam")
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'uploadedFileId', 'errors', 'warnings', 'info', 'updates'})
        self.assertListEqual(response_json['errors'], [])
        self.assertListEqual(response_json['warnings'], [])
        self.assertListEqual(
            response_json['info'], ['Parsed 3 rows in 2 individuals from samples.csv', 'No change detected for 1 rows'])
        self.assertListEqual(sorted(response_json['updates'], key=lambda o: o['individualGuid']), [
            {'individualGuid': 'I000001_na19675', 'individualId': 'NA19675_1', 'filePath': 'gs://readviz/batch_10.dcr.bed.gz', 'sampleId': 'NA19675'},
            {'individualGuid': 'I000003_na19679', 'individualId': 'NA19679', 'filePath': 'gs://readviz/NA19679.bam', 'sampleId': None},
        ])

        # test data manager access
        self.login_data_manager_user()
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.apis.igv_api.load_uploaded_file')
    def test_receive_bulk_alignment_table_handler(self, mock_load_uploaded_file):
        url = reverse(receive_bulk_igv_table_handler)
        self.check_pm_login(url)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['No file uploaded']})

        uploaded_file_id = 'test_file_id'
        request_data = json.dumps({'mappingFile': {'uploadedFileId': uploaded_file_id}})
        pm_projects_rows = [
            ['1kg project nåme with uniçøde', 'NA19675_1', 'gs://readviz/batch_10.dcr.bed.gz', 'NA19675'],
            ['1kg project nåme with uniçøde', 'NA19675_1', 'gs://readviz/NA19675_1.bam'],
            ['1kg project nåme with uniçøde', 'NA20870', 'gs://readviz/NA20870.cram'],
            ['Test Reprocessed Project', 'NA20885', 'gs://readviz/NA20885.cram'],
        ]
        rows = pm_projects_rows + [['Non-Analyst Project', 'NA21234', 'gs://readviz/NA21234.cram']]
        mock_load_uploaded_file.return_value = [['NA19675']] + rows
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Must contain 3 or 4 columns: NA19675']})

        mock_load_uploaded_file.return_value = rows + [
            ['Non-project', 'NA19675_1', 'gs://readviz/NA19679.bam'],
            ['1kg project nåme with uniçøde', 'NA19675', 'gs://readviz/batch_10.dcr.bed.gz'],
        ]
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': [
            'The following Individuals do not exist: NA19675 (1kg project nåme with uniçøde), NA21234 (Non-Analyst Project), NA19675_1 (Non-project)']})

        # Send valid request
        mock_load_uploaded_file.return_value = pm_projects_rows
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'uploadedFileId', 'errors', 'warnings', 'info', 'updates'})
        self.assertListEqual(response_json['errors'], [])
        self.assertListEqual(response_json['warnings'], [])
        self.assertListEqual(response_json['info'], ['Parsed 4 rows in 3 individuals', 'No change detected for 1 rows'])
        updates = [
            {'individualGuid': 'I000001_na19675', 'individualId': 'NA19675_1', 'filePath': 'gs://readviz/batch_10.dcr.bed.gz', 'sampleId': 'NA19675'},
            {'individualGuid': 'I000001_na19675', 'individualId': 'NA19675_1', 'filePath': 'gs://readviz/NA19675_1.bam', 'sampleId': None},
            {'individualGuid': 'I000015_na20885', 'individualId': 'NA20885', 'filePath': 'gs://readviz/NA20885.cram', 'sampleId': None},
        ]
        self.assertListEqual(sorted(response_json['updates'], key=lambda o: o['individualGuid']), updates)

        # test data manager access
        self.login_data_manager_user()
        mock_load_uploaded_file.return_value = rows
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json['info'], ['Parsed 5 rows in 4 individuals', 'No change detected for 1 rows'])
        self.assertListEqual(sorted(response_json['updates'], key=lambda o: o['individualGuid']), updates + [
            {'individualGuid': 'I000018_na21234', 'individualId': 'NA21234', 'filePath': 'gs://readviz/NA21234.cram', 'sampleId': None}
        ])

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    def test_add_alignment_sample(self, mock_local_file_exists, mock_subprocess):
        url = reverse(update_individual_igv_sample, args=['I000001_na19675'])
        self.check_pm_login(url)

        # Send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'request must contain fields: filePath')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': 'invalid_path.txt',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.reason_phrase,
            'Invalid file extension for "invalid_path.txt" - valid extensions are bam, cram, bigWig, junctions.bed.gz, bed.gz')

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
            'filePath': '/readviz/NA19675.new.cram',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'igvSamplesByGuid': {'S000145_na19675': {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000001_na19675', 'sampleGuid': 'S000145_na19675',
            'familyGuid': 'F000001_1', 'filePath': '/readviz/NA19675.new.cram', 'sampleId': None, 'sampleType': 'alignment'}}})
        mock_local_file_exists.assert_called_with('/readviz/NA19675.new.cram')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': 'gs://readviz/batch_10.dcr.bed.gz', 'sampleId': 'NA19675',
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'igvSamplesByGuid', 'individualsByGuid'})
        self.assertEqual(len(response_json['igvSamplesByGuid']), 1)
        sample_guid = next(iter(response_json['igvSamplesByGuid']))
        self.assertDictEqual(response_json['igvSamplesByGuid'][sample_guid], {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000001_na19675', 'sampleGuid': sample_guid,
            'familyGuid': 'F000001_1',  'filePath': 'gs://readviz/batch_10.dcr.bed.gz', 'sampleId': 'NA19675', 'sampleType': 'gcnv'})
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['igvSampleGuids']),
            {'S000145_na19675', sample_guid}
        )
        mock_subprocess.assert_called_with('gsutil ls gs://readviz/batch_10.dcr.bed.gz', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': 'gs://readviz/batch_10.junctions.bed.gz', 'sampleId': 'NA19675',
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(len(response_json['igvSamplesByGuid']), 1)
        junctions_sample_guid = next(iter(response_json['igvSamplesByGuid']))
        self.assertNotEqual(sample_guid, junctions_sample_guid)
        self.assertDictEqual(response_json['igvSamplesByGuid'][junctions_sample_guid], {
            'projectGuid': PROJECT_GUID, 'individualGuid': 'I000001_na19675', 'sampleGuid': junctions_sample_guid,
            'familyGuid': 'F000001_1',  'filePath': 'gs://readviz/batch_10.junctions.bed.gz', 'sampleId': 'NA19675',
            'sampleType': 'spliceJunctions'})

        # test data manager access
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'filePath': '/readviz/NA19675_new.cram',
        }))
        self.assertEqual(response.status_code, 200)

    @responses.activate
    def test_igv_genomes_proxy(self):
        url_path = 'igv.org.genomes/foo?query=true'
        s3_url = reverse(igv_genomes_proxy, args=['s3', url_path])

        expected_body = {'genes': ['GENE1', 'GENE2']}
        responses.add(
            responses.GET, 'https://s3.amazonaws.com/igv.org.genomes/foo?query=true', match_querystring=True,
            content_type='application/json', body=json.dumps(expected_body))

        response = self.client.get(s3_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.content), expected_body)
        self.assertIsNone(responses.calls[0].request.headers.get('Range'))

        # test with range header proxy
        gs_url = reverse(igv_genomes_proxy, args=['gs', 'test-bucket/foo.fasta'])
        expected_content = 'test file content'
        responses.add(
            responses.GET, 'https://storage.googleapis.com/test-bucket/foo.fasta', match_querystring=True,
            body=expected_content)

        response = self.client.get(gs_url, HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), expected_content)
        self.assertEqual(responses.calls[1].request.headers.get('Range'), 'bytes=100-200')
