import unittest
from unittest.mock import patch

import hail as hl

from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset

GNOMAD_EXOMES_37_PATH = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_exomes_37.ht'
)
GNOMAD_EXOMES_38_PATH = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_exomes_38.ht'
)


class GnomadTest(unittest.TestCase):
    def test_gnomad_exomes_37(self):
        with patch.object(
            ReferenceDataset,
            'path',
            return_value=GNOMAD_EXOMES_37_PATH,
        ):
            ht = ReferenceDataset.gnomad_exomes.get_ht(ReferenceGenome.GRCh37)
            self.assertEqual(
                ht.collect(),
                [
                    hl.Struct(
                        locus=hl.Locus(
                            contig='1',
                            position=12586,
                            reference_genome='GRCh37',
                        ),
                        alleles=['C', 'T'],
                        AF=0.0005589714855886996,
                        AN=3578,
                        AC=2,
                        Hom=0,
                        AF_POPMAX_OR_GLOBAL=0.0022026430815458298,
                        FAF_AF=9.839000267675146e-05,
                        Hemi=0,
                    ),
                ],
            )

    def test_gnomad_exomes_38(self):
        with patch.object(
            ReferenceDataset,
            'path',
            return_value=GNOMAD_EXOMES_38_PATH,
        ):
            ht = ReferenceDataset.gnomad_exomes.get_ht(ReferenceGenome.GRCh38)
            self.assertEqual(
                ht.collect(),
                [
                    hl.Struct(
                        locus=hl.Locus(
                            contig='chr1',
                            position=12138,
                            reference_genome='GRCh38',
                        ),
                        alleles=['C', 'A'],
                        AF=0.00909090880304575,
                        AN=110,
                        AC=1,
                        Hom=0,
                        AF_POPMAX_OR_GLOBAL=0.009803921915590763,
                        FAF_AF=0.0,
                        Hemi=0,
                    ),
                ],
            )
