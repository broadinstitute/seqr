import gzip
import mock
import os
import responses
import tempfile

from django.core.management import call_command

from reference_data.models import DataVersions
from seqr.views.utils.test_utils import AuthenticationTestCase


class ReferenceDataCommandTestCase(AuthenticationTestCase):
    databases = ['default', 'reference_data']
    fixtures = ['users', 'reference_data']

    URL = ''
    DATA = None

    def setUp(self):
        super().setUp()

        self.tmp_dir = tempfile.gettempdir()
        patcher = mock.patch('reference_data.utils.download_utils.tempfile')
        self.mock_tempfile = patcher.start()
        self.mock_tempfile.gettempdir.return_value = self.tmp_dir
        self.addCleanup(patcher.stop)

        self.mock_get_file_last_modified_patcher = mock.patch('reference_data.models.LoadableModel._get_file_last_modified')
        self.mock_get_file_last_modified = self.mock_get_file_last_modified_patcher.start()
        self.mock_get_file_last_modified.return_value = 'Thu, 20 Mar 2025 20:52:24 GMT'
        self.addCleanup(self.mock_get_file_last_modified_patcher.stop)
        self.mock_clingen_version_patcher = mock.patch('reference_data.models.ClinGen.get_current_version')
        self.mock_clingen_version_patcher.start().return_value = '2025-02-05'
        self.addCleanup(self.mock_clingen_version_patcher.stop)
        self.mock_hpo_version_patcher = mock.patch('reference_data.models.HumanPhenotypeOntology.get_current_version')
        self.mock_hpo_version_patcher.start().return_value = '2025-03-03'
        self.addCleanup(self.mock_hpo_version_patcher.stop)

    @responses.activate
    def _run_command(self, data, head_response=None, command_args=None):
        if data:
            body = ''.join(data)
            if self.URL.endswith('gz'):
                body = gzip.compress(body.encode())
            responses.add(responses.GET, self.URL, body=body)
        if head_response:
            responses.add(responses.HEAD, self.URL, **head_response)

        call_command('update_all_reference_data', *(command_args or []))


    def _test_update_command(self, model_name, expected_version, existing_records=1, created_records=1, skipped_records=1, head_response=None, command_args=None, version_check_download=False):
        DataVersions.objects.filter(data_model_name=model_name).delete()

        # test without a file_path parameter
        self._run_command(self.DATA, head_response=head_response, command_args=command_args)

        tmp_file = '{}/{}'.format(self.tmp_dir, self.URL.split('/')[-1])
        download_log = (f'Downloading {self.URL} to {tmp_file}', None)
        log_calls = [
            (f'Updating {model_name}', None),
            download_log,
            (f'Parsing file {tmp_file}', None),
            (f'Deleted {existing_records} {model_name} records', None),
            (f'Created {created_records} {model_name} records', None),
            ('Done', None),
            (f'Loaded {created_records} {model_name} records', None),
        ]
        if version_check_download:
            log_calls.insert(0, download_log)
        if skipped_records:
            log_calls.append((f'Skipped {skipped_records} records with unrecognized genes.', None))
        log_calls += [
            ('Done', None),
            (f'Updated: {model_name}', None),
        ]
        self.assert_json_logs(user=None, expected=log_calls)

        dv = DataVersions.objects.get(data_model_name=model_name)
        self.assertEqual(dv.version, expected_version)

        # test with a locally cached file
        dv.delete()
        self.reset_logs()
        headers = head_response['headers'] if head_response else {}
        head_response = {
            **(head_response or {}),
            'headers': {**headers, "Content-Length": f"{os.path.getsize(tmp_file)}"},
        }
        self._run_command(data=None, head_response=head_response, command_args=command_args)
        download_log_indices = [0, 2] if version_check_download else [1]
        for index in download_log_indices:
            log_calls[index] = (f'Re-using {tmp_file} previously downloaded from {self.URL}', None)
        log_calls[download_log_indices[-1] + 2] = (f'Deleted {created_records} {model_name} records', None)
        self.assert_json_logs(user=None, expected=log_calls)
