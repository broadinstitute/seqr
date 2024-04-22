import mock

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from seqr.models import VariantTagType


class CopyProjectTagsTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.copy_project_tags.logger')
    def test_command(self, mock_logger):
        # Test missing required arguments
        with self.assertRaises(CommandError) as ce:
            call_command('copy_project_tags')
        self.assertIn(str(ce.exception), ['Error: argument --source is required',
                'Error: the following arguments are required: --source, --target'])

        # Test user did confirm.
        call_command('copy_project_tags', '--source=R0001_1kg', '--target=R0002_empty')
        mock_logger.info.assert_called_with('Saved tag Excluded (new id = 7)')

        src_tags = VariantTagType.objects.filter(project__guid = 'R0001_1kg')
        target_tags = VariantTagType.objects.filter(project__guid = 'R0002_empty')
        self.assertEqual(src_tags.count(), target_tags.count())
        self.assertEqual(target_tags.all()[0].name, 'Excluded')
