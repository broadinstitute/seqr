from django.core.management import call_command
import responses

from seqr.models import Family, VariantTagType, VariantTag, Dataset
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase


class TransferFamiliesClickhouseTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    LOGS = [
        ('Disabled search for 7 samples in the following 1 families: 2', None),
        ('Triggered Delete Families', {'detail':  {'project_guid': 'R0001_1kg', 'family_guids': ['F000002_2', 'F000004_4']}}),
    ]

    @responses.activate
    def test_command(self):
        responses.add(responses.POST, 'http://pipeline-runner:6000/delete_families_enqueue', status=200)

        call_command(
            'transfer_families_to_different_project', '--from-project=R0001_1kg', '--to-project=R0003_test', '2', '4', '5', '12',
        )

        self.maxDiff = None
        self.assert_json_logs(user=None, expected=[
            ('Found 3 out of 4 families. No match for: 12.', None),
            ('Skipping 1 families with analysis groups in the project: 5 (Test Group 1)', None),
            *self.LOGS,
            ('Splitting 2 datasets', None),
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

        existing_dataset = Dataset.objects.get(guid='S000129_na19675')
        self.assertListEqual(list(existing_dataset.active_individuals.order_by('id').values_list('id', flat=True)),[1, 7, 9])
        self.assertListEqual(list(existing_dataset.inactive_individuals.order_by('id').values_list('id', flat=True)), [3])
        self.assertEqual(Dataset.objects.filter(active_individuals__family=family).count(), 0)
        datasets = {d.guid: d for d in Dataset.objects.filter(inactive_individuals__family=family).distinct()}
        self.assertEqual(len(datasets), 3)
        previous_guids = {'S000145_hg00731', 'S000149_hg00733'}
        self.assertTrue(previous_guids.issubset(set(datasets.keys())))
        split_dataset = next(d for guid, d in datasets.items() if guid not in previous_guids)
        self.assertListEqual(list(split_dataset.inactive_individuals.order_by('id').values_list('id', flat=True)),  [4, 5, 6])
        self.assertEqual(split_dataset.active_individuals.count(), 0)
        self.assertEqual(split_dataset.sample_type, 'WES')
        self.assertEqual(split_dataset.dataset_type, 'SNV_INDEL')
        self.assertEqual(split_dataset.data_source, 'test_index')
        self.assertEqual(split_dataset.loaded_date.isoformat(), '2017-02-05T06:12:55.397000+00:00')

        family = Family.objects.get(family_id='4')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 1)
