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
from loading_pipeline.lib.tasks.exports.fields import get_variant_details_export_fields
from loading_pipeline.lib.tasks.exports.misc import (
    camelcase_array_structexpression_fields,
    unmap_formatting_annotation_enums,
)
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget, GCSorLocalTarget
from loading_pipeline.lib.tasks.update_variant_annotations_table_with_new_variants import (
    UpdateVariantAnnotationsTableWithNewVariantsTask,
)
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
        if self.dataset_type.export_all_callset_variants:
            return self.clone(UpdateVariantAnnotationsTableWithNewVariantsTask)
        return self.clone(WriteNewVariantsTableTask)

    def create_table(self) -> None:
        ht = hl.read_table(
            new_variants_table_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )
        ht = unmap_formatting_annotation_enums(
            ht,
            self.reference_genome,
            self.dataset_type,
        )
        ht = camelcase_array_structexpression_fields(
            ht,
            self.reference_genome,
            self.dataset_type,
        )
        ht = ht.key_by()
        return ht.select(
            **get_variant_details_export_fields(
                ht,
                self.reference_genome,
                self.dataset_type,
            ),
        )
