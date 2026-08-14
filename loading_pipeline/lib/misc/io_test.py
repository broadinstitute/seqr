import unittest
from unittest import mock

import hail as hl

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.misc.io import (
    compute_hail_n_partitions,
    file_size_bytes,
    import_imputed_sex,
    import_vcf,
    remap_pedigree_hash,
    select_relevant_fields,
    split_multi_hts,
)
from loading_pipeline.lib.misc.validation import SeqrValidationError

TEST_IMPUTED_SEX = 'loading_pipeline/var/test/sex_check/test_imputed_sex.tsv'
TEST_IMPUTED_SEX_UNEXPECTED_VALUE = (
    'loading_pipeline/var/test/sex_check/test_imputed_sex_unexpected_value.tsv'
)
CORRUPTED_VCF = 'loading_pipeline/var/test/callsets/1kg_corrupt.vcf.gz'
TEST_INVALID_VCF = 'loading_pipeline/var/test/callsets/improperly_formatted.vcf'
TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'
TEST_MITO_MT = 'loading_pipeline/var/test/callsets/mito_1.mt'


class IOTest(unittest.TestCase):
    def test_file_size_mb(self) -> None:
        # find loading_pipeline/var/test/callsets/mito_1.mt -type f | grep -v 'crc' | xargs ls -alt {} | awk '{sum += $5; print sum}'
        # 191310
        self.assertEqual(file_size_bytes(TEST_MITO_MT), 191310)

    def test_compute_hail_n_partitions(self) -> None:
        self.assertEqual(compute_hail_n_partitions(23), 1)
        self.assertEqual(compute_hail_n_partitions(191310), 1)
        self.assertEqual(compute_hail_n_partitions(1913100000), 58)

    def test_import_imputed_sex(self) -> None:
        ht = import_imputed_sex(TEST_IMPUTED_SEX)
        self.assertListEqual(
            ht.collect(),
            [
                hl.Struct(s='abc_1', predicted_sex='M'),
                hl.Struct(s='abc_2', predicted_sex='F'),
                hl.Struct(s='abc_3', predicted_sex='U'),
                hl.Struct(s='abc_4', predicted_sex='XYY'),
                hl.Struct(s='abc_5', predicted_sex='U'),
            ],
        )

    def test_import_imputed_sex_unexpected_value(self) -> None:
        ht = import_imputed_sex(TEST_IMPUTED_SEX_UNEXPECTED_VALUE)
        self.assertRaisesRegex(
            hl.utils.java.HailUserError,
            'Found unexpected value UNKNOWN in imputed sex file',
            ht.collect,
        )

    def test_remap_pedigree_hash(self) -> None:
        self.assertEqual(
            hl.eval(
                remap_pedigree_hash(
                    TEST_PEDIGREE_3_REMAP,
                ),
            ),
            573002191,
        )

    def test_import_vcf(self) -> None:
        self.assertRaisesRegex(
            TypeError,
            'missing 1 required positional argument',
            import_vcf,
            'abc',
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'Unable to access the VCF in cloud storage',
            import_vcf,
            'bad.vcf',
            ReferenceGenome.GRCh38,
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            'Gzip-compressed data is corrupt',
            import_vcf,
            CORRUPTED_VCF,
            ReferenceGenome.GRCh38,
        )
        with mock.patch(
            'loading_pipeline.lib.misc.io.hl.read_table',
        ) as mock_read_table:
            mock_read_table.side_effect = hl.utils.java.FatalError(
                'GoogleJsonResponseException: 403 Forbidden',
            )
            self.assertRaisesRegex(
                SeqrValidationError,
                'Unable to access the VCF in cloud storage',
                import_vcf,
                'abc123/bad.vcf',
                ReferenceGenome.GRCh38,
            )
        self.assertRaisesRegex(
            SeqrValidationError,
            'VCF failed file format validation: Your input file has a malformed header: We never saw the required CHROM header line \\(starting with one #\\) for the input VCF file',
            import_vcf,
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
        )
        self.assertRaisesRegex(
            SeqrValidationError,
            "VCF failed file format validation: invalid character 'N' in integer literal",
            import_vcf,
            TEST_INVALID_VCF,
            ReferenceGenome.GRCh38,
        )

    def test_select_missing_field(self) -> None:
        self.assertRaisesRegex(
            SeqrValidationError,
            "Your callset is missing a required field: 'a magic field'",
            select_relevant_fields,
            hl.MatrixTable.from_parts(
                rows={
                    'locus': [
                        hl.Locus(
                            contig='chr1',
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                    'alleles': [
                        ['A', 'C'],
                    ],
                    'rsid': ['rs1233'],
                    'filters': [{'PASS'}],
                },
                cols={'s': ['sample_1']},
                entries={
                    'GT': [[hl.Call([0, 0])]],
                    'AD': [[[0, 20]]],
                    'GQ': [[99]],
                },
            ).key_rows_by('locus', 'alleles'),
            DatasetType.SNV_INDEL,
            {'a magic field': hl.tint32},
        )

    def test_split_multi_failure(self) -> None:
        self.assertRaisesRegex(
            SeqrValidationError,
            'Your callset failed while attempting to split multiallelic sites.  This error can occur if the dataset contains both multiallelic variants and duplicated loci.',
            split_multi_hts,
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
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                    'alleles': [
                        ['A', 'G', 'AC'],
                        ['A', 'AT', 'C', 'G'],
                    ],
                },
                cols={'s': ['sample_1']},
                entries={
                    'GQ': [[99], [98]],
                },
            )
            .key_rows_by('locus', 'alleles')
            .repartition(1),
            False,
            1,
        )

    def test_split_multi_failure_ad_length(self) -> None:
        self.assertRaisesRegex(
            SeqrValidationError,
            'Your callset failed while attempting to split multiallelic sites.  This error can occur if the provided Allele Depth \\(AD\\) field does not match the length of the multiallelic site.',
            split_multi_hts,
            hl.MatrixTable.from_parts(
                rows={
                    'locus': [
                        hl.Locus(
                            contig='chr1',
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                    'alleles': [
                        ['GAC', 'G', 'GTTTTTTTTTTTTTTTAC'],
                    ],
                },
                cols={'s': ['sample_1']},
                entries={
                    'GQ': [[99]],
                    'AD': [[[0, 1]]],
                },
            ).key_rows_by('locus', 'alleles'),
            False,
            1,
        )
