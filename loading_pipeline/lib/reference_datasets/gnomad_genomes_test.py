import unittest
from unittest.mock import patch

import hail as hl

from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset

GNOMAD_GENOMES_37_PATH = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_genomes_37.ht'
)
GNOMAD_GENOMES_38_PATH = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_genomes_38.ht'
)


class GnomadTest(unittest.TestCase):
    def test_gnomad_genomes_37(self):
        with patch.object(
            ReferenceDataset,
            'path',
            return_value=GNOMAD_GENOMES_37_PATH,
        ):
            ht = ReferenceDataset.gnomad_genomes.get_ht(ReferenceGenome.GRCh37)
            self.assertEqual(
                ht.collect(),
                [
                    hl.Struct(
                        locus=hl.Locus(
                            contig='1',
                            position=10131,
                            reference_genome='GRCh37',
                        ),
                        alleles=['CT', 'C'],
                        AF=3.6635403375839815e-05,
                        AN=27296,
                        AC=1,
                        Hom=0,
                        AF_POPMAX_OR_GLOBAL=3.6635403375839815e-05,
                        FAF_AF=0.0,
                        Hemi=0,
                    ),
                ],
            )

    def test_gnomad_genomes_38(self):
        with patch.object(
            ReferenceDataset,
            'path',
            return_value=GNOMAD_GENOMES_38_PATH,
        ):
            ht = ReferenceDataset.gnomad_genomes.get_ht(ReferenceGenome.GRCh38)
            self.assertEqual(
                ht.collect(),
                [
                    hl.Struct(
                        locus=hl.Locus(
                            contig='chr1',
                            position=10057,
                            reference_genome='GRCh38',
                        ),
                        alleles=['A', 'C'],
                        AF=2.642333674884867e-05,
                        AN=113536,
                        AC=3,
                        Hom=0,
                        AF_POPMAX_OR_GLOBAL=3.779861071961932e-05,
                        FAF_AF=7.019999884505523e-06,
                        Hemi=0,
                    ),
                ],
            )
