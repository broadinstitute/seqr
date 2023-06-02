import mock

from unittest import TestCase
from seqr.utils.file_utils import mv_file_to_gs, get_gs_file_list


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
        mock_subproc.Popen.assert_called_with('gsutil mv /temp_path gs://bucket/target_path', stdout=mock_subproc.PIPE, stderr=mock_subproc.STDOUT, shell=True)
        mock_logger.info.assert_called_with('==> gsutil mv /temp_path gs://bucket/target_path', None)
        process.wait.assert_called_with()

        mock_subproc.reset_mock()
        mock_logger.reset_mock()
        process.wait.return_value = 0
        mv_file_to_gs('/temp_path', 'gs://bucket/target_path', user=None)
        mock_subproc.Popen.assert_called_with('gsutil mv /temp_path gs://bucket/target_path', stdout=mock_subproc.PIPE, stderr=mock_subproc.STDOUT, shell=True)
        mock_logger.info.assert_called_with('==> gsutil mv /temp_path gs://bucket/target_path', None)
        process.wait.assert_called_with()

    @mock.patch('seqr.utils.file_utils.subprocess')
    @mock.patch('seqr.utils.file_utils.logger')
    def test_get_gs_file_list(self, mock_logger, mock_subproc):
        with self.assertRaises(Exception) as ee:
            get_gs_file_list('/temp_path')
        self.assertEqual(str(ee.exception),  'A Google Storage path is expected.')

        process = mock_subproc.Popen.return_value
        process.communicate.return_value = b'', b'-bash: gsutil: command not found.\nPlease check the path.\n'
        with self.assertRaises(Exception) as ee:
            get_gs_file_list('gs://bucket/target_path/', user=None)
        self.assertEqual(str(ee.exception), 'Run command failed: -bash: gsutil: command not found. Please check the path.')
        mock_subproc.Popen.assert_called_with('gsutil ls gs://bucket/target_path', stdout=mock_subproc.PIPE,
                                              stderr=mock_subproc.PIPE, shell=True)
        mock_logger.info.assert_called_with('==> gsutil ls gs://bucket/target_path', None)
        process.communicate.assert_called_with()

        mock_subproc.reset_mock()
        mock_logger.reset_mock()
        process.communicate.return_value = b'\n\nUpdates are available for some Cloud SDK components.  To install them,\n' \
                                           b'please run:\n  $ gcloud components update\ngs://bucket/target_path/id_file.txt\n' \
                                           b'gs://bucket/target_path/data.vcf.gz\n', b''
        file_list = get_gs_file_list('gs://bucket/target_path', user=None)
        mock_subproc.Popen.assert_called_with('gsutil ls gs://bucket/target_path/**', stdout=mock_subproc.PIPE,
                                              stderr=mock_subproc.PIPE, shell=True)
        mock_logger.info.assert_called_with('==> gsutil ls gs://bucket/target_path/**', None)
        process.communicate.assert_called_with()
        self.assertEqual(file_list, ['gs://bucket/target_path/id_file.txt', 'gs://bucket/target_path/data.vcf.gz'])
