from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
import mock

from seqr.models import SavedVariant, VariantTag, Project


class TransferFamiliesTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.clear_project_tags.logger.info')
    @mock.patch('seqr.management.commands.clear_project_tags.input')
    def test_command(self, mock_input, mock_logger):
        mock_input.side_effect = 'n'
        with self.assertRaises(CommandError) as ce:
            call_command('clear_project_tags', 'Test Reprocessed')
        self.assertEqual(str(ce.exception), 'User aborted')

        # Test only demo projects can be deleted
        mock_input.side_effect = 'y'
        call_command('clear_project_tags', '1kg')
        mock_input.assert_called_with('Are you sure you want to clear the tags for the following 0 projects (y/n): \n')
        mock_logger.assert_called_with('Deleted 0 entities:')

        # Test success
        mock_input.side_effect = 'y'
        call_command('clear_project_tags', 'Test Reprocessed')

        mock_input.assert_called_with(
            'Are you sure you want to clear the tags for the following 1 projects (y/n): Test Reprocessed Project\n')
        mock_logger.assert_has_calls([
            mock.call('Deleted 5 entities:'),
            mock.call('    VariantTag_saved_variants: 2'),
            mock.call('    VariantTag: 1'),
            mock.call('    SavedVariant: 2'),
        ], any_order=True)

        self.assertEqual(SavedVariant.objects.filter(family__project__guid='R0003_test').count(), 0)
        self.assertEqual(VariantTag.objects.filter(saved_variants__family__project__guid='R0003_test').count(), 0)

    @mock.patch('seqr.management.commands.clear_project_tags.logger.info')
    def test_cron_command(self, mock_logger):
        Project.objects.update(all_user_demo=True)
        call_command('clear_project_tags', 'ALL_USER_DEMO', '--skip-confirm')

        mock_logger.assert_has_calls([
            mock.call('Clearing tags for the following projects: Test Reprocessed Project'),
            mock.call('Deleted 5 entities:'),
            mock.call('    VariantTag_saved_variants: 2'),
            mock.call('    VariantTag: 1'),
            mock.call('    SavedVariant: 2'),
        ], any_order=True)

        self.assertEqual(SavedVariant.objects.filter(family__project__guid='R0003_test').count(), 0)
        self.assertEqual(VariantTag.objects.filter(saved_variants__family__project__guid='R0003_test').count(), 0)

