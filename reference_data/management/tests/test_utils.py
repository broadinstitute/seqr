import gzip
import mock
import responses
import tempfile

from django.core.management import call_command
from django.test import TestCase

class ReferenceDataCommandTestCase(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    URL = None
    DATA = None

    def setUp(self):
        patcher = mock.patch('reference_data.management.commands.utils.update_utils.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

        tmp_dir = tempfile.gettempdir()
        self.tmp_file = '{}/{}'.format(tmp_dir, self.URL.split('/')[-1])
        patcher = mock.patch('reference_data.management.commands.utils.download_utils.tempfile')
        self.mock_tempfile = patcher.start()
        self.mock_tempfile.gettempdir.return_value = tmp_dir
        self.addCleanup(patcher.stop)

    @responses.activate
    def _test_update_command(self, command_name, model_name, existing_records=1, created_records=1, skipped_records=1):
        # test without a file_path parameter
        body = ''.join(self.DATA)
        if self.URL.endswith('gz'):
            body = gzip.compress(body.encode())
        responses.add(responses.GET, self.URL, body=body)

        call_command(command_name)

        self.mock_logger.error.assert_not_called()
        log_calls = [
            mock.call('Parsing file'),
            mock.call('Deleting {} existing {} records'.format(existing_records, model_name)),
            mock.call('Creating {} {} records'.format(created_records, model_name)),
            mock.call('Done'),
            mock.call(
                'Loaded {} {} records from {}. Skipped {} records with unrecognized genes.'.format(
                    created_records, model_name, self.tmp_file, skipped_records)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        self.mock_logger.info.assert_has_calls(log_calls)

        # test with a file_path parameter
        self.mock_logger.reset_mock()
        responses.add(responses.HEAD, self.URL, headers={"Content-Length": "1024"})
        responses.remove(responses.GET, self.URL)
        call_command(command_name, self.tmp_file)
        log_calls[1] = mock.call('Deleting {} existing {} records'.format(created_records, model_name))
        self.mock_logger.info.assert_has_calls(log_calls)
