import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.callsets import get_callset_ht
from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
    new_variants_table_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.exports.fields import get_variants_export_fields
from loading_pipeline.lib.tasks.exports.misc import (
    camelcase_array_structexpression_fields,
    subset_consequences_fields,
    unmap_formatting_annotation_enums,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.update_variant_annotations_table_with_new_variants import (
    UpdateVariantAnnotationsTableWithNewVariantsTask,
)
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
        if (
            self.dataset_type.export_all_callset_variants
            # Special logic for the Clickhouse migration, forcing
            # utilization of the project subsetted variants table
            # that lives at the new variants table path.
            and len(self.project_guids) > 0
        ):
            return self.clone(UpdateVariantAnnotationsTableWithNewVariantsTask)
        return self.clone(WriteNewVariantsTableTask)

    def create_table(self) -> None:
        if (
            self.dataset_type.export_all_callset_variants
            # Special logic for the Clickhouse migration, forcing
            # utilization of the project subsetted variants table
            # that lives at the new variants table path.
            and len(self.project_guids) > 0
        ):
            ht = hl.read_table(
                variant_annotations_table_path(
                    self.reference_genome,
                    self.dataset_type,
                ),
            )
            callset_ht = get_callset_ht(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
                self.project_guids,
            )
            ht = ht.semi_join(callset_ht)
        else:
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
        if self.dataset_type.should_write_new_variant_details:
            ht = subset_consequences_fields(
                ht,
                self.reference_genome,
            )
        ht = ht.key_by()
        return ht.select(
            **get_variants_export_fields(ht, self.reference_genome, self.dataset_type),
        )
