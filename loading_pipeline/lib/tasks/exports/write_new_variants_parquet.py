import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
    new_variants_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_new_variants_table import (
    WriteNewVariantsTableTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewVariantsParquetTask(BaseWriteParquetTask):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variants_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> luigi.Task:
        return self.clone(WriteNewVariantsTableTask)

    def create_table(self) -> None:
        ht = hl.read_table(
            new_variants_table_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )
        ht = ht.key_by()
        return ht.select(
            *self.dataset_type.variants_export_field_names(self.reference_genome),
        )
