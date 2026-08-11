from unittest.mock import Mock, patch

import hail as hl
import luigi.worker

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
)
from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.misc.clickhouse import (
    ClickhouseReferenceDataset,
    get_clickhouse_client,
)
from loading_pipeline.lib.paths import (
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.variants_migration.load_clickhouse_variants_tables import (
    LoadClickhouseVariantsTablesTask,
)
from loading_pipeline.lib.tasks.variants_migration.migrate_variant_details_parquet import (
    MigrateVariantDetailsParquetTask,
)
from loading_pipeline.lib.tasks.variants_migration.migrate_variants_parquet import (
    MigrateVariantsParquetTask,
)
from loading_pipeline.lib.tasks.variants_migration.update_variant_annotations_table_with_dropped_reference_datasets import (
    UpdateVariantAnnotationsTableWithDroppedReferenceDatasetsTask,
)
from loading_pipeline.lib.test.clickhouse_schema_testcase import (
    ClickhouseSchemaTestCase,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import (
    MockedDatarootTestCase,
)

TEST_SCHEMA = 'loading_pipeline/var/test/test_clickhouse_schema.sql'
TEST_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh38/SNV_INDEL/annotations.ht'
)
TEST_RUN_ID = 'manual__2024-04-03'


class LoadClickhouseVariantsTablesTaskTest(
    MockedDatarootTestCase,
    ClickhouseSchemaTestCase,
):
    def setUp(self) -> None:
        super().setUp()
        ht = hl.read_table(TEST_SNV_INDEL_ANNOTATIONS)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
            ),
        )

    @patch.object(
        ClickhouseReferenceDataset,
        'for_reference_genome_dataset_type',
        return_value=[ClickhouseReferenceDataset.CLINVAR],
    )
    def test_write_variants_to_clickhouse(
        self,
        mock_for_reference_genome_dataset_type: Mock,
    ):
        worker = luigi.worker.Worker()
        task = UpdateVariantAnnotationsTableWithDroppedReferenceDatasetsTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        ht = hl.read_table(task.output().path)
        self.assertTrue('variant_id' in ht.row)
        self.assertTrue('gnomad_genomes' not in ht.row and 'dbnsfp' not in ht.row)

        task = MigrateVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())

        task = MigrateVariantDetailsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())

        task = MigrateVariantDetailsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())

        task = LoadClickhouseVariantsTablesTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            run_id=TEST_RUN_ID,
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.complete())

        client = get_clickhouse_client()
        variants_count = client.execute(
            f"""
            SELECT COUNT(*)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants_memory`
            """,
        )[0][0]
        self.assertEqual(variants_count, 2)
        variant_details_count = client.execute(
            f"""
            SELECT COUNT(*)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`
            """,
        )[0][0]
        self.assertEqual(variant_details_count, 2)
        key_lookups_count = client.execute(
            f"""
            SELECT COUNT(*)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/key_lookup`
            """,
        )[0][0]
        self.assertEqual(key_lookups_count, 2)
