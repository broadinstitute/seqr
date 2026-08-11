import unittest

from loading_pipeline.lib.core.definitions import ReferenceGenome


class TestReferenceGenomeProperties(unittest.TestCase):
    def test_v02_value(self):
        self.assertEqual(ReferenceGenome.GRCh37.v02_value, '37')
        self.assertEqual(ReferenceGenome.GRCh38.v02_value, '38')

    def test_hl_reference(self):
        hl_37_reference = ReferenceGenome.GRCh37.hl_reference
        self.assertEqual(hl_37_reference.name, 'GRCh37')

        hl_38_reference = ReferenceGenome.GRCh38.hl_reference
        self.assertEqual(hl_38_reference.name, 'GRCh38')

    def test_standard_contigs(self):
        expected_37_contigs = {
            '3',
            '12',
            '21',
            '2',
            '1',
            '7',
            '13',
            '8',
            '11',
            '22',
            'MT',
            '14',
            'Y',
            '18',
            '19',
            '20',
            '17',
            'X',
            '10',
            '15',
            '16',
            '4',
            '5',
            '9',
            '6',
        }
        self.assertEqual(ReferenceGenome.GRCh37.standard_contigs, expected_37_contigs)

        expected_38_contigs = {
            'chr10',
            'chr11',
            'chr17',
            'chr18',
            'chr9',
            'chr22',
            'chr3',
            'chrY',
            'chr7',
            'chr6',
            'chr13',
            'chr19',
            'chr16',
            'chrX',
            'chr12',
            'chr2',
            'chr21',
            'chr20',
            'chr8',
            'chrM',
            'chr5',
            'chr4',
            'chr14',
            'chr1',
            'chr15',
        }
        self.assertEqual(ReferenceGenome.GRCh38.standard_contigs, expected_38_contigs)

    def test_optional_contigs(self):
        self.assertEqual(ReferenceGenome.GRCh37.optional_contigs, {'Y', 'MT'})
        self.assertEqual(ReferenceGenome.GRCh38.optional_contigs, {'chrY', 'chrM'})

    def test_contig_recoding(self):
        expected_37_recode = {
            'chr1': '1',
            'chr2': '2',
            'chr3': '3',
            'chr4': '4',
            'chr5': '5',
            'chr6': '6',
            'chr7': '7',
            'chr8': '8',
            'chr9': '9',
            'chr10': '10',
            'chr11': '11',
            'chr12': '12',
            'chr13': '13',
            'chr14': '14',
            'chr15': '15',
            'chr16': '16',
            'chr17': '17',
            'chr18': '18',
            'chr19': '19',
            'chr20': '20',
            'chr21': '21',
            'chr22': '22',
            'chrX': 'X',
            'chrY': 'Y',
            'chrM': 'MT',
        }
        self.assertDictEqual(
            ReferenceGenome.GRCh37.contig_recoding(include_mt=True),
            expected_37_recode,
        )

        expected_38_recode = {
            '1': 'chr1',
            '2': 'chr2',
            '3': 'chr3',
            '4': 'chr4',
            '5': 'chr5',
            '6': 'chr6',
            '7': 'chr7',
            '8': 'chr8',
            '9': 'chr9',
            '10': 'chr10',
            '11': 'chr11',
            '12': 'chr12',
            '13': 'chr13',
            '14': 'chr14',
            '15': 'chr15',
            '16': 'chr16',
            '17': 'chr17',
            '18': 'chr18',
            '19': 'chr19',
            '20': 'chr20',
            '21': 'chr21',
            '22': 'chr22',
            'X': 'chrX',
            'Y': 'chrY',
            'MT': 'chrM',
        }
        self.assertDictEqual(
            ReferenceGenome.GRCh38.contig_recoding(include_mt=True),
            expected_38_recode,
        )
