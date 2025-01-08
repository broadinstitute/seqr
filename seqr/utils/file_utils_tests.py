import mock

from unittest import TestCase
from seqr.utils.file_utils import mv_file_to_gs


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
