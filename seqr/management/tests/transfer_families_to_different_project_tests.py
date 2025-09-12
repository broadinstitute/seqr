import responses
from django.core.management import call_command

from seqr.models import Family, VariantTagType, VariantTag, Sample
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase


class TransferFamiliesTest(object):

    DEACTIVATE_SEARCH = True
    LOGS = []

    def test_command(self):
        call_command(
            'transfer_families_to_different_project', '--from-project=R0001_1kg', '--to-project=R0003_test', '2', '4', '5', '12',
        )

        self.maxDiff = None
        self.assert_json_logs(user=None, expected=[
            ('Found 3 out of 4 families. No match for: 12.', None),
            ('Skipping 1 families with analysis groups in the project: 5 (Test Group 1)', None),
            *self.LOGS,
            ('Updating "Excluded" tags', None),
            ('Updating families', None),
            ('Done.', None),
        ])

        family = Family.objects.get(family_id='2')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 3)

        old_tag_type = VariantTagType.objects.get(name='Excluded', project__guid='R0001_1kg')
        new_tag_type = VariantTagType.objects.get(name='Excluded', project__guid='R0003_test')
        self.assertNotEqual(old_tag_type, new_tag_type)
        self.assertEqual(old_tag_type.color, new_tag_type.color)
        self.assertEqual(old_tag_type.category, new_tag_type.category)
        self.assertEqual(VariantTag.objects.filter(variant_tag_type=old_tag_type).count(), 0)
        new_tags = VariantTag.objects.filter(variant_tag_type=new_tag_type)
        self.assertEqual(len(new_tags), 1)
        self.assertEqual(new_tags[0].saved_variants.first().family, family)

        samples = Sample.objects.filter(individual__family=family)
        self.assertEqual(samples.count(), 7)
        self.assertEqual(samples.filter(is_active=True).count(), 0 if self.DEACTIVATE_SEARCH else 7)

        family = Family.objects.get(family_id='4')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 1)


class TransferFamiliesLocalTest(TransferFamiliesTest, AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    DEACTIVATE_SEARCH = False


class TransferFamiliesClickhouseTest(TransferFamiliesTest, AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    ES_HOSTNAME = ''
    LOGS = [
        ('Disabled search for 7 samples in the following 1 families: 2', None),
        ('Clickhouse does not support deleting individual families from project. Manually delete MITO data for F000002_2 in project R0001_1kg', None),
        ('Clickhouse does not support deleting individual families from project. Manually delete SNV_INDEL data for F000002_2 in project R0001_1kg', None),
        ('Clickhouse does not support deleting individual families from project. Manually delete GCNV data for F000002_2 in project R0001_1kg', None),
    ]
