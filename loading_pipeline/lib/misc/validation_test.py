import unittest
from unittest.mock import patch

import hail as hl

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.misc.validation import (
    SeqrValidationError,
    validate_allele_depth_length,
    validate_allele_type,
    validate_expected_contig_frequency,
    validate_imported_field_types,
    validate_no_duplicate_variants,
    validate_sample_type,
)

TEST_MITO_MT = 'loading_pipeline/var/test/callsets/mito_1.mt'


def _mt_from_contigs(contigs):
    return (
        hl.MatrixTable.from_parts(
            rows={
                'locus': [
                    hl.Locus(
                        contig=contig,
                        position=1,
                        reference_genome='GRCh38',
                    )
                    for contig in contigs
                ],
            },
            cols={'s': ['sample_1']},
            entries={'HL': [[0.0] for _ in range(len(contigs))]},
        )
        .key_rows_by('locus')
        .key_cols_by('s')
    )


class ValidationTest(unittest.TestCase):
    def test_validate_allele_type(self) -> None:
        mt = (
            hl.MatrixTable.from_parts(
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
                    ],
                    'alleles': [
                        ['A', 'T'],
                        # NB: star alleles should pass through this validation just fine,
                        # but are eventually filtered out upstream.
                        ['A', '*'],
                        ['A', '-'],
                        ['A', '<NON_REF>'],
                    ],
                },
                cols={'s': ['sample_1']},
                entries={'HL': [[0.0], [0.0], [0.0], [0.0]]},
            )
            .key_rows_by('locus', 'alleles')
            .key_cols_by('s')
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            "Alleles with invalid AlleleType are present in the callset: \\[\\('A', '-'\\), \\('A', '<NON_REF>'\\)\\]",
            validate_allele_type,
            mt,
            DatasetType.SNV_INDEL,
        )

        mt = (
            hl.MatrixTable.from_parts(
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
                    ],
                    'alleles': [
                        ['C', '<NON_REF>'],
                        ['A', '<NON_REF>'],
                    ],
                },
                cols={'s': ['sample_1']},
                entries={'HL': [[0.0], [0.0]]},
            )
            .key_rows_by('locus', 'alleles')
            .key_cols_by('s')
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'Alleles with invalid allele <NON_REF> are present in the callset.  This appears to be a GVCF containing records for sites with no variants.',
            validate_allele_type,
            mt,
            DatasetType.SNV_INDEL,
        )

    def test_validate_allele_depth_length(self) -> None:
        mt = (
            hl.MatrixTable.from_parts(
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
                    ],
                    'alleles': [
                        ['A', 'T'],
                        # NB: star alleles should pass through this validation just fine,
                        # but are eventually filtered out upstream.
                        ['A', 'TC', 'TG'],
                        ['A', 'TTT'],
                        ['A', 'CCC'],
                    ],
                },
                cols={'s': ['sample_1', 'sample_2']},
                entries={
                    'AD': [
                        [[1, 0], [1, 0]],
                        [[1], [1, 0, 1]],
                        [[1, 0], [1]],
                        [[1, 0], [1, 0]],
                    ],
                },
            )
            .key_rows_by('locus', 'alleles')
            .key_cols_by('s')
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            "Found variants with unequal Allele Depth array lengths over samples \\(first 10, if applicable\\): \\{'1-2-A-TC-TG': \\{1, 3\\}, '1-3-A-TTT': \\{1, 2\\}\\}",
            validate_allele_depth_length,
            mt,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )

    def test_validate_imported_field_types(self) -> None:
        mt = hl.read_matrix_table(TEST_MITO_MT)
        validate_imported_field_types(mt, DatasetType.MITO, {})
        mt = mt.annotate_cols(contamination=hl.int32(mt.contamination))
        mt = mt.annotate_entries(DP=hl.float32(mt.DP))
        mt = mt.annotate_rows(vep=hl.dict({'t': '1'}))
        self.assertRaisesRegex(
            SeqrValidationError,
            "Found unexpected field types on MatrixTable after import: \\['contamination: int32', 'DP: float32', 'vep: dict<str, str>', 'tester: missing'\\]",
            validate_imported_field_types,
            mt,
            DatasetType.MITO,
            {'tester': hl.tfloat32},
        )

    def test_validate_no_duplicate_variants(self) -> None:
        mt = (
            hl.MatrixTable.from_parts(
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
                            position=2,
                            reference_genome='GRCh38',
                        ),
                    ],
                    'alleles': [
                        ['A', 'C'],
                        ['A', 'C'],
                        ['A', 'C'],
                    ],
                },
                cols={'s': ['sample_1']},
                entries={'HL': [[0.0], [0.0], [0.0]]},
            )
            .key_rows_by('locus', 'alleles')
            .key_cols_by('s')
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            "Variants are present multiple times in the callset: \\['1-2-A-C'\\]",
            validate_no_duplicate_variants,
            mt,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )

    def test_validate_expected_contig_frequency(self) -> None:
        mt = _mt_from_contigs(ReferenceGenome.GRCh38.standard_contigs)
        self.assertIsNone(
            validate_expected_contig_frequency(mt, ReferenceGenome.GRCh38, 1),
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'Missing the following expected contigs',
            validate_expected_contig_frequency,
            mt,
            ReferenceGenome.GRCh37,
            1,
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'which is lower than expected minimum count',
            validate_expected_contig_frequency,
            mt,
            ReferenceGenome.GRCh38,
            2,
        )

        # Drop an optional contig
        mt = _mt_from_contigs(ReferenceGenome.GRCh38.standard_contigs - {'chrY'})
        self.assertIsNone(
            validate_expected_contig_frequency(mt, ReferenceGenome.GRCh38, 1),
        )

        # Drop a non-optional contig
        mt = _mt_from_contigs(ReferenceGenome.GRCh38.standard_contigs - {'chr3'})
        self.assertRaisesRegex(
            SeqrValidationError,
            'Missing the following expected contigs',
            validate_expected_contig_frequency,
            mt,
            ReferenceGenome.GRCh38,
            1,
        )

    def test_validate_sample_type(self) -> None:
        mt = _mt_from_contigs(ReferenceGenome.GRCh38.standard_contigs)
        coding_and_noncoding_variants_ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
                {
                    'locus': hl.Locus(
                        contig='chr2',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
                {
                    'locus': hl.Locus(
                        contig='chr3',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
                {
                    'locus': hl.Locus(
                        contig='chr4',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
            ],
            hl.tstruct(
                locus=hl.tlocus('GRCh38'),
                coding=hl.tbool,
                noncoding=hl.tbool,
            ),
            key='locus',
        )
        self.assertIsNone(
            validate_sample_type(
                mt,
                ReferenceGenome.GRCh38,
                SampleType.WGS,
                ['project_a'],
                coding_and_noncoding_variants_ht,
            ),
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'specified as WES but appears to be WGS',
            validate_sample_type,
            mt,
            ReferenceGenome.GRCh38,
            SampleType.WES,
            ['project_a'],
            coding_and_noncoding_variants_ht,
        )

        # has coding, but not noncoding now.
        coding_and_noncoding_variants_ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
                {
                    'locus': hl.Locus(
                        contig='chr2',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
                {
                    'locus': hl.Locus(
                        contig='chr2',
                        position=2,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
            ],
            hl.tstruct(
                locus=hl.tlocus('GRCh38'),
                coding=hl.tbool,
                noncoding=hl.tbool,
            ),
            key='locus',
        )
        self.assertIsNone(
            validate_sample_type(
                mt,
                ReferenceGenome.GRCh38,
                SampleType.WES,
                ['project_a'],
                coding_and_noncoding_variants_ht,
            ),
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'specified as WGS but appears to be WES',
            validate_sample_type,
            mt,
            ReferenceGenome.GRCh38,
            SampleType.WGS,
            ['project_a'],
            coding_and_noncoding_variants_ht,
        )

        # has noncoding, but not coding now.
        coding_and_noncoding_variants_ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
                {
                    'locus': hl.Locus(
                        contig='chr2',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
                {
                    'locus': hl.Locus(
                        contig='chr2',
                        position=2,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
            ],
            hl.tstruct(
                locus=hl.tlocus('GRCh38'),
                coding=hl.tbool,
                noncoding=hl.tbool,
            ),
            key='locus',
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'contains noncoding variants but is missing common coding variants',
            validate_sample_type,
            mt,
            ReferenceGenome.GRCh38,
            SampleType.WGS,
            ['project_a'],
            coding_and_noncoding_variants_ht,
        )

        # Validation safe if all projects are to be skipped
        with patch('loading_pipeline.lib.misc.validation.Env') as mock_env:
            mock_env.SAMPLE_TYPE_VALIDATION_EXCLUDED_PROJECTS = ['project_a']
            self.assertIsNone(
                validate_sample_type(
                    mt,
                    ReferenceGenome.GRCh38,
                    SampleType.WGS,
                    ['project_a'],
                    coding_and_noncoding_variants_ht,
                ),
            )
