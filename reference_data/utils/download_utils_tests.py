import mock
import os
import responses

import tempfile
import shutil

from reference_data.utils.download_utils import download_file

from django.test import TestCase


class DownloadUtilsTest(TestCase):

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @responses.activate
    @mock.patch('reference_data.utils.download_utils.logger')
    @mock.patch('reference_data.utils.download_utils.os.path.isfile')
    @mock.patch('reference_data.utils.download_utils.os.path.getsize')
    def test_download_file(self, mock_getsize, mock_isfile, mock_logger):
        responses.add(responses.HEAD, 'https://mock_url/test_file.gz',
                      headers={"Content-Length": "1024"}, status=200)
        responses.add(responses.HEAD, 'https://mock_url/test_file.txt',
                      headers={"Content-Length": "1024"}, status=200)
        responses.add(responses.GET, 'https://mock_url/test_file.txt', body='test data\nanother line\n')

        # Test bad url
        with self.assertRaises(ValueError) as ve:
            download_file("bad_url")
        self.assertEqual(str(ve.exception), "Invalid url: bad_url")

        # Test already downloaded
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024
        result = download_file('https://mock_url/test_file.gz')
        mock_logger.info.assert_called_with('Re-using {} previously downloaded from https://mock_url/test_file.gz'.format(result))

        mock_isfile.return_value = False
        mock_getsize.return_value = 0
        mock_logger.reset_mock()
        result = download_file('https://mock_url/test_file.txt')
        mock_logger.info.assert_called_with("Downloading https://mock_url/test_file.txt to {}".format(result))
        self.assertEqual(result, "{}/test_file.txt".format(os.path.dirname(self.test_dir)))

        with open(result, 'r') as f:
            line1 = f.readline()
            line2 = f.readline()
        self.assertEqual(line1, "test data\n")
        self.assertEqual(line2, "another line\n")
