import unittest

import hail as hl

from loading_pipeline.lib.misc.sv import (
    deduplicate_merged_sv_concordance_calls,
)

ANNOTATIONS_HT = hl.Table.parallelize(
    [
        {
            'variant_id': 'BND_chr1_6',
            'end': 20404,
            'endChrom': 'chr5',
        },
        {
            'variant_id': 'BND_chr1_9',
            'end': 789481,
            'endChrom': 'chr1',
        },
        {
            'variant_id': 'CPX_chr1_22',
            'end': 6559723,
            'endChrom': 'chr1',
        },
    ],
    hl.tstruct(
        variant_id=hl.tstr,
        end=hl.tint32,
        endChrom=hl.tstr,
    ),
    key='variant_id',
)


class SVTest(unittest.TestCase):
    def test_deduplicate_merged_sv_concordance_calls(self) -> None:
        mt = (
            hl.MatrixTable.from_parts(
                rows={
                    'variant_id': [
                        'new_v1',
                        'new_v2',
                        'new_v3',
                    ],
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
                    ],
                    'info.END': [
                        1,
                        2,
                        3,
                    ],
                    'info.END2': [
                        1,
                        2,
                        3,
                    ],
                    'info.CHR2': [
                        'chr1',
                        'chr1',
                        'chr1',
                    ],
                    'info.SEQR_INTERNAL_TRUTH_VID': [
                        'BND_chr1_6',
                        'BND_chr1_9',
                        'CPX_chr1_22',
                    ],
                },
                cols={'s': ['sample_1']},
                entries={'GQ': [[99] for _ in range(3)]},
            )
            .key_rows_by('variant_id')
            .key_cols_by('s')
        )
        mt = deduplicate_merged_sv_concordance_calls(
            mt,
            ANNOTATIONS_HT,
        )
        self.assertEqual(
            mt['info.SEQR_INTERNAL_TRUTH_VID'].collect(),
            [
                'BND_chr1_6',
                'BND_chr1_9',
                'CPX_chr1_22',
            ],
        )

        mt = (
            hl.MatrixTable.from_parts(
                rows={
                    'variant_id': [
                        'new_v1',
                        'new_v2',
                        'new_v3',
                        'new_v4',
                    ],
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
                    ],
                    'info.END': [
                        1,
                        2,
                        789481,
                        789485,
                    ],
                    'info.END2': [
                        1,
                        2,
                        789481,
                        789485,
                    ],
                    'info.CHR2': [
                        'chr1',
                        'chr1',
                        'chr2',
                        'chr1',
                    ],
                    'info.SEQR_INTERNAL_TRUTH_VID': [
                        'BND_chr1_6',
                        'BND_chr1_9',
                        'BND_chr1_9',
                        'BND_chr1_9',
                    ],
                },
                cols={'s': ['sample_1']},
                entries={'GQ': [[99] for _ in range(4)]},
            )
            .key_rows_by('variant_id')
            .key_cols_by('s')
        )
        mt = deduplicate_merged_sv_concordance_calls(
            mt,
            ANNOTATIONS_HT,
        )
        self.assertEqual(
            mt['info.SEQR_INTERNAL_TRUTH_VID'].collect(),
            [
                'BND_chr1_6',
                None,
                None,
                'BND_chr1_9',
            ],
        )
