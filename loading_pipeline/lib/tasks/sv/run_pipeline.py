import luigi
import luigi.util

from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.sv.write_new_entries_parquet import (
    WriteNewSvEntriesParquetTask,
)
from loading_pipeline.lib.tasks.sv.write_new_variants_parquet import (
    WriteNewSvVariantsParquetTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class RunSvPipelineTask(luigi.WrapperTask):
    attempt_id = luigi.IntParameter()

    def requires(self):
        return [
            self.clone(WriteMetadataForSvRunTask),
            self.clone(WriteNewSvEntriesParquetTask),
            self.clone(WriteNewSvVariantsParquetTask),
        ]
