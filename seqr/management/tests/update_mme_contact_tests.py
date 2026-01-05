from django.core.management import call_command, CommandError
from django.test import TestCase
from io import StringIO
import mock

from matchmaker.models import MatchmakerSubmission


class TransferFamiliesTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.update_mme_contact.logger.info')
    def test_command(self, mock_logger):
        out = StringIO()
        with self.assertRaises(CommandError) as err:
            call_command('update_mme_contact', stdout=out)
        self.assertEqual(str(err.exception), 'Error: the following arguments are required: email')

        call_command(
            'update_mme_contact', 'UDNCC@hms.harvard.edu', '--replace-email', 'test_user@broadinstitute.org',
            '--replace-name', 'Test User',
        )
        mock_logger.assert_has_calls([
            mock.call('Updated 1 submissions'),
            mock.call('Done'),
        ])
        expected_contacts = [
            {'name': '', 'email': 'matchmaker@phenomecentral.org'},
            {'name': 'Test User', 'email': 'test_user@broadinstitute.org'},
        ]
        self.assertEqual(
            MatchmakerSubmission.objects.get(id=3).contacts, expected_contacts,
        )

        mock_logger.reset_mock()
        call_command('update_mme_contact', 'test_user@broadinstitute.org')
        mock_logger.assert_has_calls([
            mock.call('Updated 1 submissions'),
            mock.call('Skipped updating submissions with no remaining valid contacts: P0004515'),
            mock.call('Done'),
        ])
        self.assertEqual( MatchmakerSubmission.objects.get(id=3).contacts, expected_contacts)
        self.assertEqual(MatchmakerSubmission.objects.get(id=1).contacts, [{'name': 'Sam Baxter', 'email': 'matchmaker@broadinstitute.org'}])

