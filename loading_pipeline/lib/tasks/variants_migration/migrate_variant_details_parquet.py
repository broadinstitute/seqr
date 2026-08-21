import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    new_variant_details_parquet_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc import (
    BaseRunJobOnDataprocTask,
)
from loading_pipeline.lib.tasks.exports.fields import (
    get_variant_details_export_fields,
)
from loading_pipeline.lib.tasks.exports.misc import (
    camelcase_array_structexpression_fields,
    unmap_formatting_annotation_enums,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.variants_migration.update_variant_annotations_table_with_dropped_reference_datasets import (
    UpdateVariantAnnotationsTableWithDroppedReferenceDatasetsTask,
)


@luigi.util.inherits(BaseLoadingPipelineParams)
class MigrateVariantDetailsParquetTask(BaseWriteParquetTask):
    run_id = luigi.Parameter()
    attempt_id = luigi.IntParameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variant_details_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> luigi.Task:
        return self.clone(UpdateVariantAnnotationsTableWithDroppedReferenceDatasetsTask)

    def create_table(self) -> None:
        ht = hl.read_table(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
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


class MigrateVariantDetailsParquetOnDataprocTask(BaseRunJobOnDataprocTask):
    @property
    def task(self) -> luigi.Task:
        return MigrateVariantDetailsParquetTask
