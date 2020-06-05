from __future__ import unicode_literals

from django.core.management import call_command
from django.test import TestCase
import mock

from seqr.models import Family, VariantTagType, VariantTag


class TransferFamiliesTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.transfer_families_to_different_project.logger.info')
    def test_command(self, mock_loger):
        call_command(
            'transfer_families_to_different_project', '--from-project=R0001_1kg', '--to-project=R0003_test', '12', '2',
        )

        mock_loger.assert_has_calls([
            mock.call('Found 1 out of 2 families. No match for: 12.'),
            mock.call('Updating "Known gene for phenotype" tags'),
            mock.call('Updating families'),
            mock.call('Done.'),
        ])

        family = Family.objects.get(family_id='2')
        self.assertEqual(family.project.guid, 'R0003_test')

        old_tag_type = VariantTagType.objects.get(name='Known gene for phenotype', project__guid='R0001_1kg')
        new_tag_type = VariantTagType.objects.get(name='Known gene for phenotype', project__guid='R0003_test')
        self.assertNotEqual(old_tag_type, new_tag_type)
        self.assertEqual(old_tag_type.color, new_tag_type.color)
        self.assertEqual(old_tag_type.category, new_tag_type.category)
        self.assertEqual(VariantTag.objects.filter(variant_tag_type=old_tag_type).count(), 0)
        new_tags = VariantTag.objects.filter(variant_tag_type=new_tag_type)
        self.assertEqual(len(new_tags), 1)
        self.assertEqual(new_tags[0].saved_variants.first().family, family)
