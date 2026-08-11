import unittest

import hail as hl

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, Sex
from loading_pipeline.lib.misc.io import import_callset, select_relevant_fields
from loading_pipeline.lib.misc.pedigree import Family, Sample
from loading_pipeline.lib.misc.sample_ids import subset_samples
from loading_pipeline.lib.misc.sv import (
    deduplicate_merged_sv_concordance_calls,
    overwrite_male_non_par_calls,
)

TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1.vcf'
ANNOTATIONS_HT = hl.Table.parallelize(
    [
        {
            'variant_id': 'BND_chr1_6',
            'algorithms': 'manta',
            'end_locus': hl.Locus(
                contig='chr5',
                position=20404,
                reference_genome='GRCh38',
            ),
        },
        {
            'variant_id': 'BND_chr1_9',
            'algorithms': 'manta',
            'end_locus': hl.Locus(
                contig='chr1',
                position=789481,
                reference_genome='GRCh38',
            ),
        },
        {
            'variant_id': 'CPX_chr1_22',
            'algorithms': 'manta',
            'end_locus': hl.Locus(
                contig='chr1',
                position=6559723,
                reference_genome='GRCh38',
            ),
        },
    ],
    hl.tstruct(
        variant_id=hl.tstr,
        algorithms=hl.tstr,
        end_locus=hl.tlocus('GRCh38'),
    ),
    key='variant_id',
)


class SVTest(unittest.TestCase):
    def test_overwrite_male_non_par_calls(self) -> None:
        mt = import_callset(TEST_SV_VCF, ReferenceGenome.GRCh38, DatasetType.SV)
        mt = select_relevant_fields(
            mt,
            DatasetType.SV,
        )
        mt = subset_samples(
            mt,
            hl.Table.parallelize(
                [{'s': sample_id} for sample_id in ['RGP_164_1', 'RGP_164_2']],
                hl.tstruct(s=hl.dtype('str')),
                key='s',
            ),
        )
        mt = overwrite_male_non_par_calls(
            mt,
            {
                Family(
                    family_guid='family_1',
                    samples={
                        'RGP_164_1': Sample(sample_id='RGP_164_1', sex=Sex.FEMALE),
                        'RGP_164_2': Sample(sample_id='RGP_164_2', sex=Sex.MALE),
                    },
                ),
            },
        )
        mt = mt.filter_rows(mt.locus.contig == 'chrX')
        self.assertEqual(
            [
                hl.Locus(contig='chrX', position=3, reference_genome='GRCh38'),
                hl.Locus(contig='chrX', position=2781700, reference_genome='GRCh38'),
            ],
            mt.locus.collect(),
        )
        self.assertEqual(
            [
                hl.Call(alleles=[0, 0], phased=False),
                # END of this variant < start of the non-par region.
                hl.Call(alleles=[0, 1], phased=False),
                hl.Call(alleles=[0, 0], phased=False),
                hl.Call(alleles=[1], phased=False),
            ],
            mt.GT.collect(),
        )
        self.assertFalse(
            hasattr(mt, 'start_locus'),
        )

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
