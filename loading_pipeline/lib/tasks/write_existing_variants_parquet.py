import luigi
import luigi.util

from loading_pipeline.lib.misc.clickhouse import export_existing_variants_to_parquet
from loading_pipeline.lib.paths import existing_variants_parquet_path
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.exports.fields import get_existing_variants_export_field
from loading_pipeline.lib.tasks.files import (
    GCSorLocalFolderTarget,
    GCSorLocalTarget,
)


@luigi.util.inherits(BaseLoadingPipelineParams)
class WriteExistingVariantsParquetTask(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            existing_variants_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def run(self):
        export_select_fields = get_existing_variants_export_field(self.dataset_type)
        export_existing_variants_to_parquet(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
            export_select_fields,
        )
