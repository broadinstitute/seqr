import luigi
import luigi.util

from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.exports.write_new_entries_parquet import (
    WriteNewEntriesParquetTask,
)
from loading_pipeline.lib.tasks.exports.write_new_variant_details_parquet import (
    WriteNewVariantDetailsParquetTask,
)
from loading_pipeline.lib.tasks.exports.write_new_variants_parquet import (
    WriteNewVariantsParquetTask,
)
from loading_pipeline.lib.tasks.write_metadata_for_run import WriteMetadataForRunTask


@luigi.util.inherits(BaseLoadingRunParams)
class RunPipelineTask(luigi.WrapperTask):
    attempt_id = luigi.IntParameter()

    def requires(self):
        return [
            self.clone(WriteMetadataForRunTask),
            self.clone(WriteNewEntriesParquetTask),
            self.clone(WriteNewVariantsParquetTask),
            *(
                [self.clone(WriteNewVariantDetailsParquetTask)]
                if self.dataset_type.should_write_new_variant_details
                else []
            ),
        ]
