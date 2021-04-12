import mock
import datetime

from django.core.management import call_command
from django.test import TestCase


@mock.patch('reference_data.management.commands.run_reference_data_database_backup.logger')
@mock.patch('reference_data.management.commands.run_reference_data_database_backup.os')
@mock.patch('reference_data.management.commands.run_reference_data_database_backup.datetime')
class RunReferenceDataDbBackupTest(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    def test_reference_data_db_backup_command(self, mock_datetime, mock_os, mock_logger):
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 1)

        call_command('run_reference_data_database_backup',
                     '--postgres-host=test_host')

        mock_os.environ.get.assert_called_with('POSTGRES_SERVICE_HOSTNAME', 'unknown')

        calls = [
            mock.call(
                '/usr/bin/pg_dump -U postgres --host test_host reference_data_db | gzip -c - > gene_reference_data_backup.gz'),
            mock.call('gsutil mv gene_reference_data_backup.gz gs://seqr-reference-data/gene_reference_data_backup.gz')
        ]
        mock_os.system.assert_has_calls(calls)

        calls = [
            mock.call('====================================='),
            mock.call('======== 2020-04-27__20-16-01 ======= '),
            mock.call('====================================='),
            mock.call('/usr/bin/pg_dump -U postgres --host test_host reference_data_db | gzip -c - > gene_reference_data_backup.gz'),
            mock.call('gsutil mv gene_reference_data_backup.gz gs://seqr-reference-data/gene_reference_data_backup.gz')
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with timestamped file name
        mock_os.reset_mock()
        mock_os.environ.get.return_value = 'test_env_host'

        call_command('run_reference_data_database_backup', '--timestamp-name')

        mock_os.environ.get.assert_called_with('POSTGRES_SERVICE_HOSTNAME', 'unknown')

        calls = [
            mock.call(
                '/usr/bin/pg_dump -U postgres --host test_env_host reference_data_db | gzip -c - > gene_reference_data_backup_2020-04-27__20-16-01.gz'),
            mock.call('gsutil mv gene_reference_data_backup_2020-04-27__20-16-01.gz gs://seqr-reference-data/gene_reference_data_backup_2020-04-27__20-16-01.gz')
        ]
        mock_os.system.assert_has_calls(calls)
