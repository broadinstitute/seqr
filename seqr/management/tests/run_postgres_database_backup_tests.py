# -*- coding: utf-8 -*-
import mock
import datetime

from django.core.management import call_command
from django.test import TestCase


@mock.patch('seqr.management.commands.run_postgres_database_backup.logger')
@mock.patch('seqr.management.commands.run_postgres_database_backup.os')
@mock.patch('seqr.management.commands.run_postgres_database_backup.datetime')
class RunProtgresDatabaseBackupTest(TestCase):

    # Test the command without an argument
    def test_command_no_argument(self, mock_datetime, mock_os, mock_logger):
        mock_os.path.isdir.return_value = False
        mock_os.environ.get.side_effect = ['db_back_bucket', 'localhost', 'unknown']
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 1)
        call_command('run_postgres_database_backup')

        mock_os.mkdir.assert_called_with('/postgres_backups')
        calls = [
            mock.call('DATABASE_BACKUP_BUCKET', 'unknown'),
            mock.call('POSTGRES_SERVICE_HOSTNAME', 'unknown'),
            mock.call('DEPLOYMENT_TYPE', 'unknown'),
        ]
        mock_os.environ.get.assert_has_calls(calls)
        calls = [
            mock.call('====================================='),
            mock.call('======== 2020-04-27__20-16-01 ======= '),
            mock.call('====================================='),
            mock.call('Creating directory: /postgres_backups'),
            mock.call('/usr/bin/pg_dump -U postgres --host localhost seqrdb | gzip -c - > /postgres_backups/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz'),
            mock.call('/usr/local/bin/gsutil mv /postgres_backups/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz gs://db_back_bucket/postgres/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil mv /postgres_backups/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz gs://db_back_bucket/postgres/seqrdb_unknown_backup_2020-04-27__20-16-01.txt.gz')

    # Test the command with different arguments
    def test_command_with_arguments(self, mock_datetime, mock_os, mock_logger):
        mock_os.path.isdir.return_value = True
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 1)
        call_command('run_postgres_database_backup', '--bucket=test_bucket',
                     '--postgres-host=test_host',
                     '--deployment-type=test_deployment')

        mock_os.mkdir.assert_not_called()
        calls = [
            mock.call('====================================='),
            mock.call('======== 2020-04-27__20-16-01 ======= '),
            mock.call('====================================='),
            mock.call('/usr/bin/pg_dump -U postgres --host test_host seqrdb | gzip -c - > /postgres_backups/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz'),
            mock.call('/usr/local/bin/gsutil mv /postgres_backups/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz gs://test_bucket/postgres/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil mv /postgres_backups/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz gs://test_bucket/postgres/seqrdb_test_deployment_backup_2020-04-27__20-16-01.txt.gz')
