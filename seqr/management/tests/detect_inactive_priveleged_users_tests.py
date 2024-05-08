from anymail.exceptions import AnymailError
from datetime import datetime
from django.core.management import call_command
from django.contrib.auth.models import User
from django.test import TestCase
import mock

WARNING_EMAIL = """
Hi there Test Data Manager - 

You have not logged in to seqr in 75 days. Unless you log in within the next 15 days, your account will be deactivated.
"""

DEACTIVATED_EMAIL = """
Hi there Test Superuser - 

You have not logged in to seqr in 136 days, and therefore your account has been deactivated.
Please feel free to reach out to the seqr team if you would like your account reinstated.
"""

class DetectInactivePrivilegedUsersTest(TestCase):
    fixtures = ['users']

    @mock.patch('django.contrib.auth.models.send_mail')
    @mock.patch('seqr.management.commands.detect_inactive_privileged_users.logger')
    @mock.patch('seqr.management.commands.detect_inactive_privileged_users.datetime')
    def test_command(self, mock_datetime, mock_logger, mock_send_mail):
        mock_datetime.now.return_value = datetime(2020, 7, 27, 0, 0, 0)
        mock_send_mail.side_effect = [None, AnymailError('Connection error')]

        call_command('detect_inactive_privileged_users')

        self.assertFalse(User.objects.get(email='test_superuser@test.com').is_active)
        self.assertTrue(User.objects.get(email='test_data_manager@broadinstitute.org').is_active)

        mock_send_mail.assert_has_calls([
            mock.call('Warning: seqr account deactivation', WARNING_EMAIL, None, ['test_data_manager@broadinstitute.org']),
            mock.call('Warning: seqr account deactivated', DEACTIVATED_EMAIL, None, ['test_superuser@test.com']),
        ])

        mock_logger.error.assert_called_with('Unable to send email: Connection error')
        mock_logger.info.assert_has_calls([
            mock.call('Checking for inactive users'),
            mock.call('Warning test_data_manager@broadinstitute.org of impending account inactivation'),
            mock.call('Inactivating account for test_superuser@test.com'),
            mock.call('Inactive user check complete'),
        ])
