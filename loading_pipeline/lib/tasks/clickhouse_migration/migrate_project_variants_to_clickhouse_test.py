import hail as hl
import hailtop.fs as hfs
import luigi.worker
import pandas as pd

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.paths import (
    new_variant_details_parquet_path,
    new_variants_parquet_path,
    pipeline_run_success_file_path,
    project_table_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.clickhouse_migration.migrate_project_variants_to_clickhouse import (
    MigrateProjectVariantsToClickHouseTask,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import (
    MockedDatarootTestCase,
)

TEST_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh37/SNV_INDEL/annotations.ht'
)
TEST_PROJECT_TABLE = 'loading_pipeline/var/test/exports/GRCh37/SNV_INDEL/projects/WGS/R0113_test_project.ht'

TEST_RUN_ID = 'migration_run'


class WriteVariantsToClickHouseTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        ht = hl.read_table(TEST_SNV_INDEL_ANNOTATIONS)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
            ),
        )
        ht = hl.read_table(TEST_PROJECT_TABLE)
        ht.write(
            project_table_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
                SampleType.WGS,
                'R0113_test_project',
            ),
        )

    def test_migrate_variants_to_clickhouse_test(
        self,
    ) -> None:
        worker = luigi.worker.Worker()
        task = MigrateProjectVariantsToClickHouseTask(
            reference_genome=ReferenceGenome.GRCh37,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
            sample_type=SampleType.WGS,
            project_guid='R0113_test_project',
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        self.assertEqual(df.shape[0], 1)
        df = pd.read_parquet(
            new_variant_details_parquet_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        self.assertEqual(df.shape[0], 1)
        self.assertFalse(
            hfs.exists(
                pipeline_run_success_file_path(
                    ReferenceGenome.GRCh37,
                    DatasetType.SNV_INDEL,
                    TEST_RUN_ID,
                ),
            ),
        )
