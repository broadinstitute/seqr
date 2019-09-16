import mock
from unittest import TestCase
from seqr.views.utils.proxy_request_utils import proxy_to_igv

MOCK_REQUEST = mock.MagicMock()
MOCK_REQUEST.META = {'HTTP_RANGE': 'bytes=100-200'}
MOCK_REQUEST.method = 'GET'
MOCK_REQUEST.scheme = 'http'

STREAMING_READS_CONTENT = ['a', 'b', 'c']

MOCK_RESPONSE = mock.MagicMock()
MOCK_RESPONSE.raw.read.return_value = STREAMING_READS_CONTENT
MOCK_RESPONSE.status_code = 200


class ProxyRequestUtilsTest(TestCase):

    @mock.patch('seqr.views.utils.proxy_request_utils.google_bucket_file_iter')
    @mock.patch('seqr.views.utils.proxy_request_utils.requests.Session')
    def test_proxy_to_igv(self, mock_session, mock_google_bucket_file_iter):
        mock_google_bucket_file_iter.return_value = STREAMING_READS_CONTENT
        mock_session.return_value.get.return_value = MOCK_RESPONSE

        # test google bucket
        response = proxy_to_igv('gs://project_A/sample_1.bam.bai', {}, MOCK_REQUEST)
        self.assertEqual(response.status_code, 206)
        self.assertListEqual([val for val in response.streaming_content], STREAMING_READS_CONTENT)
        mock_google_bucket_file_iter.assert_called_with('gs://project_A/sample_1.bai', byte_range=(100, 200))

        # test cram
        response = proxy_to_igv('project_A/sample_1.cram', {'options': '-b,-H'}, MOCK_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'abc')
        mock_session.return_value.get.assert_called_with(
            'http://broad-seqr:5000/alignments?reference=igvjs/static/data/public/Homo_sapiens_assembly38.fasta&file=igvjs/static/data/readviz-mounts/project_A/sample_1.cram&options=-b,-H&region=',
            headers={'Range': 'bytes=100-200', 'Host': 'broad-seqr:5000'}, data=None, auth=None, stream=True, verify=True)
