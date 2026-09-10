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
from loading_pipeline.lib.tasks.exports.fields import get_variants_export_fields
from loading_pipeline.lib.tasks.exports.misc import (
    camelcase_array_structexpression_fields,
    subset_consequences_fields,
)
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
        ht = camelcase_array_structexpression_fields(
            ht,
            self.reference_genome,
            self.dataset_type,
        )
        if self.dataset_type.should_write_new_variant_details:
            ht = subset_consequences_fields(
                ht,
                self.reference_genome,
            )
        ht = ht.key_by()
        return ht.select(
            **get_variants_export_fields(ht, self.reference_genome, self.dataset_type),
        )
