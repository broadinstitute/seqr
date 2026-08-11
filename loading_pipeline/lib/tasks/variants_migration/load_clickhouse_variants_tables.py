import luigi
import luigi.util

from loading_pipeline.lib.core import FeatureFlag
from loading_pipeline.lib.misc.clickhouse import (
    ClickhouseReferenceDataset,
    ClickHouseTable,
    TableNameBuilder,
    logged_query,
)
from loading_pipeline.lib.misc.retry import retry
from loading_pipeline.lib.paths import (
    new_variant_details_parquet_path,
    new_variants_parquet_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget
from loading_pipeline.lib.tasks.variants_migration.migrate_variant_details_parquet import (
    MigrateVariantDetailsParquetOnDataprocTask,
    MigrateVariantDetailsParquetTask,
)
from loading_pipeline.lib.tasks.variants_migration.migrate_variants_parquet import (
    MigrateVariantsParquetOnDataprocTask,
    MigrateVariantsParquetTask,
)


@retry()
def refresh_seqr_variants_and_search(
    table_name_builder: TableNameBuilder,
    clickhouse_reference_dataset: ClickhouseReferenceDataset,
):
    if clickhouse_reference_dataset.has_seqr_variants:
        logged_query(
            f"""
            SYSTEM START VIEW {clickhouse_reference_dataset.all_variants_to_seqr_variants_mv(table_name_builder)}
            """,
        )
        logged_query(
            f"""
            SYSTEM REFRESH VIEW {clickhouse_reference_dataset.all_variants_to_seqr_variants_mv(table_name_builder)}
            """,
        )
        logged_query(
            f"""
            SYSTEM WAIT VIEW {clickhouse_reference_dataset.all_variants_to_seqr_variants_mv(table_name_builder)}
            """,
            timeout=clickhouse_reference_dataset.all_variants_mv_timeout,
        )
    clickhouse_reference_dataset.refresh_search(table_name_builder)


@luigi.util.inherits(BaseLoadingPipelineParams)
class LoadClickhouseVariantsTablesTask(luigi.WrapperTask):
    run_id = luigi.Parameter()
    attempt_id = luigi.IntParameter()

    def requires(self) -> luigi.Task:
        tasks = (
            [
                self.clone(MigrateVariantsParquetOnDataprocTask),
            ]
            if FeatureFlag.RUN_PIPELINE_ON_DATAPROC
            else [
                self.clone(MigrateVariantsParquetTask),
            ]
        )
        if self.dataset_type.should_write_new_variant_details:
            tasks.append(
                self.clone(MigrateVariantDetailsParquetOnDataprocTask)
                if FeatureFlag.RUN_PIPELINE_ON_DATAPROC
                else self.clone(MigrateVariantDetailsParquetTask),
            )
        return tasks

    def complete(self) -> bool:
        table_name_builder = TableNameBuilder(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        )
        if not (
            GCSorLocalFolderTarget(
                new_variant_details_parquet_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.run_id,
                ),
            ).exists()
        ) or not (
            GCSorLocalFolderTarget(
                new_variants_parquet_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.run_id,
                ),
            ).exists()
        ):
            return False
        max_key = logged_query(
            f"""
            SELECT max(key) FROM {table_name_builder.src_table(ClickHouseTable.VARIANTS_MEMORY)}
            """,
        )[0][0]
        return logged_query(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM {table_name_builder.dst_table(ClickHouseTable.VARIANTS_MEMORY)} where key = %(max_key)s
            )
            """,
            {'max_key': max_key},
        )[0][0]

    def run(self) -> None:
        table_name_builder = TableNameBuilder(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        )
        for clickhouse_table in ClickHouseTable.for_dataset_type(
            self.dataset_type,
        ):
            if clickhouse_table == ClickHouseTable.ENTRIES:
                continue
            clickhouse_table.insert(table_name_builder=table_name_builder)
        for (
            clickhouse_reference_dataset
        ) in ClickhouseReferenceDataset.for_reference_genome_dataset_type(
            self.reference_genome,
            self.dataset_type,
        ):
            refresh_seqr_variants_and_search(
                table_name_builder,
                clickhouse_reference_dataset,
            )
