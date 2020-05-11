# -*- coding: utf-8 -*-
import mock
from io import BytesIO
import datetime

from django.core.management import call_command
from django.test import TestCase


@mock.patch('seqr.management.commands.run_postgres_database_backup.os')
@mock.patch('seqr.management.commands.run_postgres_database_backup.datetime')
class RunProtgresDatabaseBackupTest(TestCase):

    # Test the command without an argument
    def test_command_no_argument(self, mock_datetime, mock_os):
        out = BytesIO()

        mock_os.path.isdir.return_value = False
        mock_os.environ.get.side_effect = ['db_back_bucket', 'localhost', 'unknown']
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 01)
        call_command('run_postgres_database_backup', stdout = out)

        mock_os.mkdir.assert_called_with('/postgres_backups')
        calls = [
            mock.call('DATABASE_BACKUP_BUCKET'),
            mock.call('POSTGRES_SERVICE_HOSTNAME', 'localhost'),
            mock.call('DEPLOYMENT_TYPE', 'local'),
        ]
        mock_os.environ.get.assert_has_calls(calls)
        self.assertEqual(
            '=====================================\n' +
            '======== 2020-04-27__20-16-01 ======= \n' +
            '=====================================\n' +
            'Creating directory: /postgres_backups\n' +
            'pg_dump -U postgres --host localhost seqrdb | gzip -c - > /postgres_backups/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz\n' +
            'gsutil cp /postgres_backups/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz gs://db_back_bucket/postgres/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz\n' +
            'pg_dump -U postgres --host localhost xwiki | gzip -c - > /postgres_backups/xwiki_unknown_backup_2020-04-27__20-16-01.txt.gz\n' +
            'gsutil cp /postgres_backups/xwiki_unknown_backup_2020-04-27__20-16-01.txt.gz gs://db_back_bucket/postgres/xwiki_unknown_backup_2020-04-27__20-16-01.txt.gz\n',
            out.getvalue())

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil -m cp /postgres_backups/xwiki_unknown_backup_2020-04-27__20-16-01.txt.gz gs://db_back_bucket/postgres/xwiki_unknown_backup_2020-04-27__20-16-01.txt.gz')

    # Test the command with different arguments
    def test_command_with_arguments(self, mock_datetime, mock_os):
        out = BytesIO()

        mock_os.path.isdir.return_value = True
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 01)
        call_command('run_postgres_database_backup', '--bucket=test_bucket',
                     '--postgres-host=test_host',
                     '--deployment-type=test_deployment',
                     stdout = out)

        mock_os.mkdir.assert_not_called()
        self.assertEqual(
            '=====================================\n' +
            '======== 2020-04-27__20-16-01 ======= \n' +
            '=====================================\n' +
            'pg_dump -U postgres --host test_host seqrdb | gzip -c - > /postgres_backups/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz\n' +
            'gsutil cp /postgres_backups/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz gs://test_bucket/postgres/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz\n' +
            'pg_dump -U postgres --host test_host xwiki | gzip -c - > /postgres_backups/xwiki_test_deployment_backup_2020-04-27__20-16-01.txt.gz\n' +
            'gsutil cp /postgres_backups/xwiki_test_deployment_backup_2020-04-27__20-16-01.txt.gz gs://test_bucket/postgres/xwiki_test_deployment_backup_2020-04-27__20-16-01.txt.gz\n',
            out.getvalue())

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil mv /postgres_backups/xwiki_test_deployment_backup_2020-04-27__20-16-01.txt.gz gs://test_bucket/postgres/xwiki_test_deployment_backup_2020-04-27__20-16-01.txt.gz')
