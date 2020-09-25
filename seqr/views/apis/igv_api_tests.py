import mock
import subprocess
from django.urls.base import reverse
from seqr.views.apis.igv_api import fetch_igv_track
from seqr.views.utils.test_utils import AuthenticationTestCase

STREAMING_READS_CONTENT = [b'CRAM\x03\x83', b'\\\t\xfb\xa3\xf7%\x01', b'[\xfc\xc9\t\xae']


class IgvAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_proxy_google_to_igv(self, mock_subprocess):
        mock_subprocess.return_value.stdout = STREAMING_READS_CONTENT

        url = reverse(fetch_igv_track, args=['R0001_1kg', 'gs://project_A/sample_1.bam.bai'])
        self.check_collaborator_login(url)
        response = self.client.get(url, HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 206)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_subprocess.assert_called_with(
            'gsutil cat -r 100-200 gs://project_A/sample_1.bai',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        url = reverse(fetch_igv_track, args=['R0001_1kg', 'gs://fc-secure-project_A/sample_1.cram.gz'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_subprocess.assert_called_with(
            'gsutil -u anvil-datastorage cat gs://fc-secure-project_A/sample_1.cram.gz | gunzip -c -q - ',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    @mock.patch('seqr.utils.file_utils.open')
    def test_proxy_local_to_igv(self, mock_open):
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.__iter__.return_value = STREAMING_READS_CONTENT
        mock_file.tell.side_effect = [0, 100, 200]

        url = reverse(fetch_igv_track, args=['R0001_1kg', '/project_A/sample_1.bam.bai'])
        self.check_collaborator_login(url)
        response = self.client.get(url, HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 206)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT[:2])
        mock_open.assert_called_with('/project_A/sample_1.bai', 'rb')
        mock_file.seek.assert_called_with(100)

        # test no byte range
        mock_file.reset_mock()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_open.assert_called_with('/project_A/sample_1.bai', 'rb')
        mock_file.seek.assert_not_called()

