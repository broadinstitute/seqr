from django.test import TestCase

from seqr.models import Individual, Project
from seqr.views.apis.samples_api import _compute_edit_distance, \
    _find_individual_id_with_lowest_edit_distance, find_matching_individuals


# don't create a test database
#import settings
#del settings.DATABASES['default']


class SamplesAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def setUp(self):
        self.individual_records_dict = {
            "NA19675": Individual(individual_id="NA19675"),
            "NA19678": Individual(),
            "NA19679": Individual(),
            "NA20881": Individual(),
            "NA20885": Individual(),
            "NA20888": Individual(),
            "HG00731": Individual(),
            "HG00732": Individual(),
            "HG00733": Individual(),
            "NA20870": Individual(),
            "NA20872": Individual(),
            "NA20874": Individual(),
            "NA20875": Individual(),
            "NA20876": Individual(),
            "NA20877": Individual(),
            "NA20878": Individual(),
        }

    def test_compute_edit_distance(self):
        self.assertEqual(_compute_edit_distance('', ''), 0)
        self.assertEqual(_compute_edit_distance('abcdefg', 'abcdefg'), 0)
        self.assertEqual(_compute_edit_distance('a', ''), 1)
        self.assertEqual(_compute_edit_distance('', 'a'), 1)
        self.assertEqual(_compute_edit_distance('a', 'b'), 1)
        self.assertEqual(_compute_edit_distance('a', 'A'), 1)
        self.assertEqual(_compute_edit_distance('abc', 'abb'), 1)
        self.assertEqual(_compute_edit_distance('abcdefg', 'abxdeyg'), 2)
        self.assertEqual(_compute_edit_distance('abcdefg', 'abdeg'), 2)
        self.assertEqual(_compute_edit_distance('abcdefg', 'd'), 6)

    def test_find_individual_id_with_lowest_edit_distance(self):

        self.assertRaisesRegex(ValueError, "No matches.*", lambda:
            _find_individual_id_with_lowest_edit_distance(
                "random_id", self.individual_records_dict, max_edit_distance=3, case_sensitive=True))
        self.assertRaisesRegex(ValueError, "Too many matches.*", lambda:
            _find_individual_id_with_lowest_edit_distance(
                "NA208", self.individual_records_dict, max_edit_distance=3, case_sensitive=True))

        individual_id, individual = _find_individual_id_with_lowest_edit_distance(
            "N19675", self.individual_records_dict, max_edit_distance=3, case_sensitive=True)
        self.assertEquals(individual_id, "NA19675")

        # test case_sensitive arg
        self.assertRaisesRegex(ValueError, "No matches.*", lambda:
            _find_individual_id_with_lowest_edit_distance(
                "na19675", self.individual_records_dict, max_edit_distance=0, case_sensitive=True))

        individual_id, individual = _find_individual_id_with_lowest_edit_distance(
            "na19675", self.individual_records_dict, max_edit_distance=0, case_sensitive=False)
        self.assertEquals(individual_id, "NA19675")

    def test_find_matching_individuals(self):
        project = Project.objects.get(guid='R0001_1kg')
        sample_ids = ["N20876", "NA20877", "NA20878", "random_id"]
        sample_id_to_individual_record = find_matching_individuals(
            project,
            sample_ids,
            max_edit_distance=1,
            individual_ids_to_exclude=["NA20878"]
        )

        self.assertEqual(len(sample_id_to_individual_record), 2)
        self.assertSetEqual({'NA20876', 'NA20877'}, set(sample_id_to_individual_record.keys()))
        first_value = next(iter(sample_id_to_individual_record.values()))
        self.assertTrue(isinstance(first_value, Individual))
