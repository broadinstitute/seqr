import mock
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.igv_api import fetch_igv_track
from seqr.views.utils.test_utils import _check_login

STREAMING_READS_CONTENT = ['a', 'b', 'c']


class IgvAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.utils.file_utils.google_bucket_file_iter')
    def test_proxy_to_igv(self, mock_google_bucket_file_iter):
        mock_google_bucket_file_iter.return_value = STREAMING_READS_CONTENT

        url = reverse(fetch_igv_track, args=['R0001_1kg', 'gs://project_A/sample_1.bam.bai'])
        _check_login(self, url)
        response = self.client.get(url, HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 206)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_google_bucket_file_iter.assert_called_with('gs://project_A/sample_1.bai', byte_range=(100, 200))

