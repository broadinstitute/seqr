import gzip
import mock
import tempfile

from unittest import TestCase
from seqr.utils.file_utils import mv_file_to_gs, file_iter


class FileUtilsTest(TestCase):

    @mock.patch('seqr.utils.file_utils.subprocess')
    @mock.patch('seqr.utils.file_utils.logger')
    def test_mv_file_to_gs(self, mock_logger, mock_subproc):
        with self.assertRaises(Exception) as ee:
            mv_file_to_gs('/temp_path', '/another_path', user=None)
        self.assertEqual(str(ee.exception),  'A Google Storage path is expected.')

        process = mock_subproc.Popen.return_value
        process.wait.return_value = -1
        process.stdout = [b'-bash: gsutil: command not found.\n', b'Please check the path.\n']
        with self.assertRaises(Exception) as ee:
            mv_file_to_gs('/temp_path', 'gs://bucket/target_path', user=None)
        self.assertEqual(str(ee.exception), 'Run command failed: -bash: gsutil: command not found. Please check the path.')
        mock_subproc.Popen.assert_called_with('gsutil mv /temp_path gs://bucket/target_path', stdout=mock_subproc.PIPE, stderr=mock_subproc.STDOUT, shell=True)  # nosec
        mock_logger.info.assert_called_with('==> gsutil mv /temp_path gs://bucket/target_path', None)
        process.wait.assert_called_with()

        mock_subproc.reset_mock()
        mock_logger.reset_mock()
        process.wait.return_value = 0
        mv_file_to_gs('/temp_path', 'gs://bucket/target_path', user=None)
        mock_subproc.Popen.assert_called_with('gsutil mv /temp_path gs://bucket/target_path', stdout=mock_subproc.PIPE, stderr=mock_subproc.STDOUT, shell=True)  # nosec
        mock_logger.info.assert_called_with('==> gsutil mv /temp_path gs://bucket/target_path', None)
        process.wait.assert_called_with()


    def test_file_iter_byte_range(self):
        content = b'test_content\ntest_content_line2\ntest_content3'
        with tempfile.NamedTemporaryFile(delete=True, mode='wb') as tmp:
            tmp.write(content)
            tmp.flush()
            self.assertEqual(
                [
                    line for line in file_iter(tmp.name, (0, 34))
                ], 
                [b'test_content\n', b'test_content_line2\n', b'tes']
            )


        with tempfile.NamedTemporaryFile(delete=True, mode='wb', suffix=".gz") as tmp:
            with gzip.GzipFile(fileobj=tmp, mode='wb') as gz:
                gz.write(content)
            tmp.flush()
            self.assertEqual(
                list(file_iter(tmp.name, (0, 40))),
                []
            )
            self.assertEqual(
                list(file_iter(tmp.name, (0, 80))),
                [b'test_content\n', b'test_content_line2\n', b'test_content3']
            )
