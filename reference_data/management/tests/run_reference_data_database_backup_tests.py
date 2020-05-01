import mock
from io import BytesIO
import datetime

from django.core.management import call_command
from django.test import TestCase


@mock.patch('reference_data.management.commands.run_reference_data_database_backup.os')
@mock.patch('reference_data.management.commands.run_reference_data_database_backup.datetime')
class RunReferenceDataDbBackupTest(TestCase):
    fixtures = ['users', 'reference_data']

    def test_reference_data_db_backup_command(self, mock_datetime, mock_os):
        out = BytesIO()

        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 01)

        call_command('run_reference_data_database_backup',
                     '--postgres-host=test_host',
                     stdout = out)

        mock_os.environ.get.assert_called_with('POSTGRES_SERVICE_HOSTNAME', 'unknown')

        calls = [
            mock.call(
                '/usr/bin/pg_dump -U postgres --host test_host reference_data_db | gzip -c - > gene_reference_data_backup.gz'),
            mock.call('gsutil mv gene_reference_data_backup.gz gs://seqr-reference-data/gene_reference_data_backup.gz')
        ]
        mock_os.system.assert_has_calls(calls)

        self.assertEqual(
            '=====================================\n' +
            '======== 2020-04-27__20-16-01 ======= \n' +
            '=====================================\n' +
            '/usr/bin/pg_dump -U postgres --host test_host reference_data_db | gzip -c - > gene_reference_data_backup.gz\n' +
            'gsutil mv gene_reference_data_backup.gz gs://seqr-reference-data/gene_reference_data_backup.gz\n',
            out.getvalue())
