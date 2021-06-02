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
            'update_mme_contact', 'seqr+udncc@populationgenomics.org.au', '--replace-email', 'seqr+test_user@populationgenomics.org.au',
        )
        mock_logger.assert_has_calls([
            mock.call('Updating 1 submissions'),
            mock.call('Done'),
        ])
        self.assertEqual(
            MatchmakerSubmission.objects.get(id=3).contact_href,
            'mailto:seqr+test_user@populationgenomics.org.au,matchmaker+phenomecentral@populationgenomics.org.au',
        )

        mock_logger.reset_mock()
        call_command('update_mme_contact', 'seqr+test_user@populationgenomics.org.au')
        mock_logger.assert_has_calls([
            mock.call('Updating 2 submissions'),
            mock.call('Done'),
        ])
        self.assertEqual( MatchmakerSubmission.objects.get(id=3).contact_href, 'mailto:matchmaker+phenomecentral@populationgenomics.org.au')
        self.assertEqual(MatchmakerSubmission.objects.get(id=1).contact_href, 'mailto:matchmaker@populationgenomics.org.au')

