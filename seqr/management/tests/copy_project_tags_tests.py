from io import BytesIO

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from seqr.models import VariantTagType


class CopyProjectTagsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_command(self):
        out = BytesIO()
        # Test missing required arguments
        with self.assertRaises(CommandError) as ce:
            call_command('copy_project_tags')
        self.assertEqual(ce.exception.message, 'Error: argument --source is required')

        # Test user did confirm.
        call_command('copy_project_tags', '--source=R0001_1kg', '--target=R0003_test', stdout=out)
        out_str = out.getvalue()
        self.assertEqual('Saved tag Known gene for phenotype (new id = 5)\n', out_str)

        src_tags = VariantTagType.objects.filter(project__guid = 'R0001_1kg')
        target_tags = VariantTagType.objects.filter(project__guid = 'R0003_test')
        self.assertEqual(src_tags.count(), target_tags.count())
        self.assertEqual(target_tags.all()[0].name, 'Known gene for phenotype')
