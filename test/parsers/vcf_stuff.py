from xbrowse.parsers import vcf_stuff
from xbrowse import Genotype

import unittest


class BasicVCFGenotypeTests(unittest.TestCase):

    def setUp(self):
        self.format_map = vcf_stuff.get_format_map('GT:AD:DP:GQ:PL')

    def test_valid_genotype(self):
        geno_str = "0/0:321,0:321:8.98:0,9,71"
        expected = Genotype(
            alleles=['A', 'A'],
            gq=8.98,
            num_alt=0,
            filter='asdf',
            ab=0,
            extras={
                'dp': '321',
                'pl': '0,9,71',
                'ad': '321,0',
            }
        )
        genotype = vcf_stuff.get_genotype_from_str(geno_str, self.format_map, 0, {'0': 'A', '1': 'T'}, vcf_filter='asdf')
        self.assertEqual(genotype, expected)


if __name__ == '__main__':
    unittest.main()