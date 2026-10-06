import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    new_variant_details_parquet_path,
    new_variants_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget, GCSorLocalTarget
from loading_pipeline.lib.tasks.write_new_variants_table import (
    WriteNewVariantsTableTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewVariantDetailsParquetTask(BaseWriteParquetTask):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variant_details_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

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
            **{
                name: getattr(ht, field)
                for name, field in self.dataset_type.variant_details_export_fields(
                    self.reference_genome,
                ).items()
            },
        )
