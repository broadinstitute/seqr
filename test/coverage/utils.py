import unittest

from xbrowse.reference.classes import CodingRegion
from xbrowse.coverage.utils import fill_in_missing_intervals
from xbrowse.coverage.classes import CoverageInterval


class FillInMissingIntervals(unittest.TestCase):

    def setUp(self):
        self.coding_region = CodingRegion('GENE1', 1, 1e9+101, 1e9+200)

    def test_no_intervals(self):
        full = fill_in_missing_intervals(self.coding_region, [])
        self.assertEqual(full[0], CoverageInterval(1e9+101, 1e9+200, 'low_coverage'))

    def test_full_interval(self):
        full = fill_in_missing_intervals(self.coding_region, [CoverageInterval(1e9+101, 1e9+200, 'callable')])
        self.assertEqual(full[0], CoverageInterval(1e9+101, 1e9+200, 'callable'))

    def test_missing_ends(self):
        full = fill_in_missing_intervals(self.coding_region, [CoverageInterval(1e9+121, 1e9+180, 'callable')])
        self.assertEqual(full[0], CoverageInterval(1e9+101, 1e9+120, 'low_coverage'))
        self.assertEqual(full[1], CoverageInterval(1e9+121, 1e9+180, 'callable'))
        self.assertEqual(full[2], CoverageInterval(1e9+181, 1e9+200, 'low_coverage'))

if __name__ == '__main__':
    unittest.main()