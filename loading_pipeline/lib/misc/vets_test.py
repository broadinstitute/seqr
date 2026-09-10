import unittest

import hail as hl

from loading_pipeline.lib.misc.io import split_multi_hts
from loading_pipeline.lib.misc.vets import (
    annotate_vets,
)


class VetsTest(unittest.TestCase):
    def test_annotate_vets(self) -> None:
        gatk_mt = hl.MatrixTable.from_parts(
            rows={
                'locus': [
                    hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                ],
                'filters': [
                    hl.set(['NO_HQ_GENOTYPES']),
                ],
            },
            cols={'s': ['sample_1']},
            entries={'HL': [[0.0]]},
        ).key_rows_by('locus')
        gatk_mt = annotate_vets(gatk_mt)
        dragen_mt = hl.MatrixTable.from_parts(
            rows={
                'locus': [
                    hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    hl.Locus(
                        contig='chr1',
                        position=2,
                        reference_genome='GRCh38',
                    ),
                    hl.Locus(
                        contig='chr1',
                        position=3,
                        reference_genome='GRCh38',
                    ),
                    hl.Locus(
                        contig='chr1',
                        position=4,
                        reference_genome='GRCh38',
                    ),
                    hl.Locus(
                        contig='chr1',
                        position=5,
                        reference_genome='GRCh38',
                    ),
                    hl.Locus(
                        contig='chr1',
                        position=6,
                        reference_genome='GRCh38',
                    ),
                ],
                'alleles': [
                    ['A', 'T'],
                    ['A', 'T'],
                    ['A', 'T'],
                    ['AC', 'T'],
                    ['AT', 'ATC'],
                    ['AG', 'ATG'],
                ],
                'filters': [
                    hl.set(['NO_HQ_GENOTYPES']),
                    hl.empty_set(hl.tstr),
                    hl.missing(hl.tset(hl.tstr)),
                    hl.set(['NO_HQ_GENOTYPES']),
                    hl.empty_set(hl.tstr),
                    hl.set(['NO_HQ_GENOTYPES']),
                ],
                'info.CALIBRATION_SENSITIVITY': [
                    ['0.999'],
                    ['0.995'],
                    ['0.999'],
                    ['0.98'],
                    ['0.99'],
                    ['0.991'],
                ],
            },
            cols={'s': ['sample_1']},
            entries={'HL': [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0]]},
        ).key_rows_by('locus', 'alleles')
        dragen_mt = split_multi_hts(dragen_mt, False)
        dragen_mt = annotate_vets(dragen_mt)
        self.assertListEqual(
            dragen_mt.filters.collect(),
            [
                {'NO_HQ_GENOTYPES', 'high_CALIBRATION_SENSITIVITY_SNP'},
                set(),
                {'high_CALIBRATION_SENSITIVITY_SNP'},
                {'NO_HQ_GENOTYPES'},
                set(),
                {'NO_HQ_GENOTYPES', 'high_CALIBRATION_SENSITIVITY_INDEL'},
            ],
        )
