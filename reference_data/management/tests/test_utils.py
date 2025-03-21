import gzip
import mock
import os
import responses
import tempfile

from django.core.management import call_command
from django.test import TestCase

from reference_data.models import DataVersions

class ReferenceDataCommandTestCase(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    URL = ''
    DATA = None

    def setUp(self):
        patcher = mock.patch('reference_data.models.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

        tmp_dir = tempfile.gettempdir()
        self.tmp_file = '{}/{}'.format(tmp_dir, self.URL.split('/')[-1])
        patcher = mock.patch('reference_data.utils.download_utils.tempfile')
        self.mock_tempfile = patcher.start()
        self.mock_tempfile.gettempdir.return_value = tmp_dir
        self.addCleanup(patcher.stop)

        patcher = mock.patch('reference_data.models.LoadableModel._get_file_last_modified')
        self.mock_get_file_last_modified = patcher.start()
        self.mock_get_file_last_modified.return_value = 'Thu, 20 Mar 2025 20:52:24 GMT'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.models.ClinGen.get_current_version')
        patcher.start().return_value = '2025-02-05'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.models.HumanPhenotypeOntology.get_current_version')
        patcher.start().return_value = '2025-03-03'
        self.addCleanup(patcher.stop)

    @responses.activate
    def _test_update_command(self, model_name, existing_records=1, created_records=1, skipped_records=1, skipped_message='genes.'):
        DataVersions.objects.filter(data_model_name=model_name).delete()

        # test without a file_path parameter
        body = ''.join(self.DATA)
        if self.URL.endswith('gz'):
            body = gzip.compress(body.encode())
        responses.add(responses.GET, self.URL, body=body)

        call_command('update_all_reference_data')

        self.mock_logger.error.assert_not_called()
        log_calls = [
            mock.call(f'Updating {model_name}'),
            mock.call(f'Parsing file {self.tmp_file}'),
            mock.call(f'Deleted {existing_records} {model_name} records'),
            mock.call(f'Created {created_records} {model_name} records'),
            mock.call('Done'),
            mock.call(f'Loaded {created_records} {model_name} records'),
            mock.call(f'Skipped {skipped_records} records with unrecognized {skipped_message}'),
        ]
        self.mock_logger.info.assert_has_calls(log_calls)

        # test with a locally cached file
        DataVersions.objects.get(data_model_name=model_name).delete()
        self.mock_logger.reset_mock()
        responses.add(responses.HEAD, self.URL, headers={"Content-Length": f"{os.path.getsize(self.tmp_file)}"})
        responses.remove(responses.GET, self.URL)
        call_command('update_all_reference_data')
        log_calls[2] = mock.call(f'Deleted {created_records} {model_name} records')
        self.mock_logger.info.assert_has_calls(log_calls)
