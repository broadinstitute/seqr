import unittest
from unittest.mock import patch

import hailtop.fs as hfs

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.paths import (
    imported_callset_path,
    metadata_for_run_path,
    new_variants_table_path,
    project_pedigree_path,
    project_table_path,
    relatedness_check_table_path,
    remapped_and_subsetted_callset_path,
    sex_check_table_path,
    tdr_metrics_path,
    validation_errors_for_run_path,
    variant_annotations_table_path,
)

TEST_VCF = 'loading_pipeline/var/test/callsets/1kg_30varia*.vcf'


class TestPaths(unittest.TestCase):
    def test_project_table_path(self) -> None:
        self.assertEqual(
            project_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.MITO,
                SampleType.WES,
                'R0652_pipeline_test',
            ),
            '/var/seqr/pipeline-data/GRCh38/MITO/projects/WES/R0652_pipeline_test.ht',
        )
        with (
            patch('loading_pipeline.lib.paths.Env') as mock_env,
        ):
            mock_env.PIPELINE_DATA_DIR = '/var/bucket/'
            self.assertEqual(
                project_table_path(
                    ReferenceGenome.GRCh37,
                    DatasetType.SNV_INDEL,
                    SampleType.WES,
                    'R0652_pipeline_test',
                ),
                '/var/bucket/GRCh37/SNV_INDEL/projects/WES/R0652_pipeline_test.ht',
            )

    def test_sex_check_table_path(self) -> None:
        self.assertEqual(
            sex_check_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                '/var/abc.efg/callset.vcf.gz',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/SNV_INDEL/sex_check/f92b8ab6b5b8c41fa20d7d49a5626b96dcd2ba79fa6f61eab7ffb80d550d951c.ht',
        )

    def test_relatedness_check_table_path(self) -> None:
        self.assertEqual(
            relatedness_check_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                '/var/abc.efg/callset.vcf.gz',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/SNV_INDEL/relatedness_check/f92b8ab6b5b8c41fa20d7d49a5626b96dcd2ba79fa6f61eab7ffb80d550d951c.ht',
        )

    def test_validation_errors_for_run_path(self) -> None:
        self.assertEqual(
            validation_errors_for_run_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'manual__2023-06-26T18:30:09.349671+00:00',
            ),
            '/var/seqr/pipeline-data/GRCh38/SNV_INDEL/runs/manual__2023-06-26T18:30:09.349671+00:00/validation_errors.json',
        )

    def test_metadata_for_run_path(self) -> None:
        self.assertEqual(
            metadata_for_run_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'manual__2023-06-26T18:30:09.349671+00:00',
            ),
            '/var/seqr/pipeline-data/GRCh38/SNV_INDEL/runs/manual__2023-06-26T18:30:09.349671+00:00/metadata.json',
        )

    def test_variant_annotations_table_path(self) -> None:
        self.assertEqual(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
            ),
            '/var/seqr/pipeline-data/GRCh38/GCNV/annotations.ht',
        )

    def test_remapped_and_subsetted_callset_path(self) -> None:
        self.assertEqual(
            remapped_and_subsetted_callset_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                '/var/abc.efg/callset.vcf.gz',
                'R0111_tgg_bblanken_wes',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/GCNV/remapped_and_subsetted_callsets/R0111_tgg_bblanken_wes/f92b8ab6b5b8c41fa20d7d49a5626b96dcd2ba79fa6f61eab7ffb80d550d951c.mt',
        )
        self.assertEqual(
            remapped_and_subsetted_callset_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                '/var/abc.efg/callset/*.vcf.gz',
                'R0111_tgg_bblanken_wes',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/GCNV/remapped_and_subsetted_callsets/R0111_tgg_bblanken_wes/26f481b386721f9889250c6549905660728ec9f77be4b8f7eeb6c4facc76282e.mt',
        )

    def test_imported_callset_path(self) -> None:
        self.assertEqual(
            imported_callset_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                '/var/abc.efg/callset.vcf.gz',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/SNV_INDEL/imported_callsets/f92b8ab6b5b8c41fa20d7d49a5626b96dcd2ba79fa6f61eab7ffb80d550d951c.mt',
        )

        with patch('loading_pipeline.lib.paths.hfs.ls') as mock_ls:
            mock_ls.return_value = [
                hfs.stat_result.FileListEntry(
                    path='loading_pipeline/var/test/callsets/1kg_30variants.vcf',
                    owner=None,
                    size=1732033623.804012,
                    typ=hfs.stat_result.FileType(2),
                    modification_time=1732033000,
                ),
            ]
            self.assertEqual(
                imported_callset_path(
                    ReferenceGenome.GRCh38,
                    DatasetType.SNV_INDEL,
                    TEST_VCF,
                ),
                '/var/seqr/seqr-loading-temp/GRCh38/SNV_INDEL/imported_callsets/01327e46c8747f15feaad2c08875b928c274dcb248ad40837ea3f49d8b4dedfb.mt',
            )

    def test_tdr_metrics_path(self) -> None:
        self.assertEqual(
            tdr_metrics_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'datarepo-7242affb.datarepo_RP_3053',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/SNV_INDEL/tdr_metrics/datarepo-7242affb.datarepo_RP_3053.tsv',
        )

    def test_new_variants_table_path(self) -> None:
        self.assertEqual(
            new_variants_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'manual__2023-06-26T18:30:09.349671+00:00',
            ),
            '/var/seqr/pipeline-data/GRCh38/SNV_INDEL/runs/manual__2023-06-26T18:30:09.349671+00:00/new_variants.ht',
        )

    def test_project_pedigree_path(self) -> None:
        self.assertEqual(
            project_pedigree_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                SampleType.WES,
                'R0652_pipeline_test',
            ),
            '/var/seqr/seqr-loading-temp/GRCh38/GCNV/pedigrees/WES/R0652_pipeline_test_pedigree.tsv',
        )
