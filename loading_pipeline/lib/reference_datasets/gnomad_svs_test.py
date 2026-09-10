import unittest
from unittest.mock import patch

import hail as hl

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset

TEST_GNOMAD_SVS_RAW_HT = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_svs_from_vcf.ht'
)


class GnomadSVsTest(unittest.TestCase):
    @patch('loading_pipeline.lib.reference_datasets.gnomad_svs.vcf_to_ht')
    def test_gnomad_svs(self, mock_vcf_to_ht):
        mock_vcf_to_ht.return_value = hl.read_table(TEST_GNOMAD_SVS_RAW_HT)
        ht = ReferenceDataset.gnomad_svs.get_ht(ReferenceGenome.GRCh38)
        self.assertEqual(
            ht.collect(),
            [
                hl.Struct(
                    KEY='gnomAD-SV_v3_BND_chr1_1a45f73a',
                    locus=hl.Locus(
                        contig='chr1',
                        position=10434,
                        reference_genome=ReferenceGenome.GRCh38,
                    ),
                    alleles=['N', '<BND>'],
                    AF=0.11413399875164032,
                    AC=8474,
                    AN=74246,
                    N_HET=8426,
                    N_HOM=24,
                ),
                hl.Struct(
                    KEY='gnomAD-SV_v3_BND_chr1_3fa36917',
                    locus=hl.Locus(
                        contig='chr1',
                        position=10440,
                        reference_genome=ReferenceGenome.GRCh38,
                    ),
                    alleles=['N', '<BND>'],
                    AF=0.004201000090688467,
                    AC=466,
                    AN=110936,
                    N_HET=466,
                    N_HOM=0,
                ),
                hl.Struct(
                    KEY='gnomAD-SV_v3_BND_chr1_7bbf34b5',
                    locus=hl.Locus(
                        contig='chr1',
                        position=10464,
                        reference_genome=ReferenceGenome.GRCh38,
                    ),
                    alleles=['N', '<BND>'],
                    AF=0.03698499873280525,
                    AC=3119,
                    AN=84332,
                    N_HET=3115,
                    N_HOM=2,
                ),
                hl.Struct(
                    KEY='gnomAD-SV_v3_BND_chr1_933a2971',
                    locus=hl.Locus(
                        contig='chr1',
                        position=10450,
                        reference_genome=ReferenceGenome.GRCh38,
                    ),
                    alleles=['N', '<BND>'],
                    AF=0.3238990008831024,
                    AC=21766,
                    AN=67200,
                    N_HET=21616,
                    N_HOM=75,
                ),
                hl.Struct(
                    KEY='gnomAD-SV_v3_DUP_chr1_01c2781c',
                    locus=hl.Locus(
                        contig='chr1',
                        position=10000,
                        reference_genome=ReferenceGenome.GRCh38,
                    ),
                    alleles=['N', '<DUP>'],
                    AF=0.0019970000721514225,
                    AC=139,
                    AN=69594,
                    N_HET=139,
                    N_HOM=0,
                ),
            ],
        )
