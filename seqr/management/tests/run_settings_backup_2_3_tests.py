# -*- coding: utf-8 -*-
from  __future__ import unicode_literals

import mock
from io import StringIO
import datetime

from django.core.management import call_command
from django.test import TestCase


@mock.patch('seqr.management.commands.run_settings_backup.os')
@mock.patch('seqr.management.commands.run_settings_backup.datetime')
class RunSettingsBackupTest(TestCase):

    # Test the command without an argument
    def test_command_no_argument(self, mock_datetime, mock_os):
        out = StringIO()

        mock_os.environ.get.side_effect = ['setting_back_bucket', 'unknown']
        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 1)
        call_command('run_settings_backup', stdout = out)

        mock_os.chdir.assert_called_with('/')
        calls = [
            mock.call('DATABASE_BACKUP_BUCKET', 'unknown'),
            mock.call('DEPLOYMENT_TYPE', 'unknown'),
        ]
        mock_os.environ.get.assert_has_calls(calls)
        self.assertEqual(
            'tar czf seqr_unknown_settings_2020-04-27__20-16-01.tar.gz /seqr_static_files\n' +
            '/usr/local/bin/gsutil mv seqr_unknown_settings_2020-04-27__20-16-01.tar.gz gs://setting_back_bucket/settings/\n',
            out.getvalue())

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil mv seqr_unknown_settings_2020-04-27__20-16-01.tar.gz gs://setting_back_bucket/settings/')

    # Test the command with different arguments
    def test_command_with_arguments(self, mock_datetime, mock_os):
        out = StringIO()

        mock_datetime.datetime.now.return_value = datetime.datetime(2020, 4, 27, 20, 16, 1)
        call_command('run_settings_backup', '--bucket=test_bucket',
                     '--deployment-type=test_deployment',
                     stdout = out)

        mock_os.chdir.assert_called_with('/')
        self.assertEqual(
            'tar czf seqr_test_deployment_settings_2020-04-27__20-16-01.tar.gz /seqr_static_files\n' +
            '/usr/local/bin/gsutil mv seqr_test_deployment_settings_2020-04-27__20-16-01.tar.gz gs://test_bucket/settings/\n',
            out.getvalue())

        mock_os.system.assert_called_with(
            '/usr/local/bin/gsutil mv seqr_test_deployment_settings_2020-04-27__20-16-01.tar.gz gs://test_bucket/settings/')
