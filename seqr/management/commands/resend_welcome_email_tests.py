# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

from django.core.management.base import CommandError

TEST_USER_EMAIL = 'test_user@test.com'
REFERRER_EMAIL = 'test_user_no_staff@test.com'


class ResendWelcomeEmailTest(TestCase):
    @mock.patch('seqr.utils.communication_utils.send_welcome_email')
    @mock.patch('django.contrib.auth.models.User')
    def test_command(self, mock_user, mock_send_welcome_email):
        mock_user.objects.get.side_effect = ['user', 'referrer']
        call_command('resend_welcome_email', '--email-address={}'.format(TEST_USER_EMAIL),
                     '--referrer={}'.format(REFERRER_EMAIL))
        calls = [
            mock.call(email__iexact=TEST_USER_EMAIL),
            mock.call(email__iexact = REFERRER_EMAIL),
        ]
        mock_user.objects.get.assert_has_calls(calls)
        mock_send_welcome_email.assert_called_with('user', 'referrer')

    def test_command_exceptions(self):
        with self.assertRaises(CommandError) as ce:
            call_command('resend_welcome_email', '--email-address={}'.format(TEST_USER_EMAIL))
        self.assertEqual(ce.exception.message, 'Error: argument -r/--referrer is required')

        with self.assertRaises(CommandError) as ce:
            call_command('resend_welcome_email', '--referrer={}'.format(REFERRER_EMAIL))
        self.assertEqual(ce.exception.message, 'Error: argument -e/--email-address is required')
