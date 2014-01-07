from xbrowse.core.genome_subset import GenomeSubsetFilter
from xbrowse.core.variants import Variant
import unittest


class FilterVariantsFromSimpleSubset(unittest.TestCase):

    def setUp(self):
        intervals = [
            (1e9+1000, 1e9+2000),
            (2e9+1000, 2e9+2000)
        ]
        self.genomesubset = GenomeSubsetFilter(intervals)

    def test_filter_variants_both_sides(self):
        v1 = Variant(1e9+1, 'A', 'T')
        v2 = Variant(1e9+1000, 'A', 'T')
        v3 = Variant(1e9+2001, 'A', 'T')
        v4 = Variant(2e9+2000, 'A', 'T')
        v5 = Variant(3e9+1, 'A', 'T')
        results = [t[1] for t in self.genomesubset.filter_variant_list([v1, v2, v3, v4, v5])]
        self.assertEqual(results, [0,1,0,1,0])


if __name__ == '__main__':
    unittest.main()