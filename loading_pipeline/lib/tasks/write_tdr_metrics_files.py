import luigi
import luigi.util

from loading_pipeline.lib.misc.terra_data_repository import gen_bq_table_names
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.write_tdr_metrics_file import WriteTDRMetricsFileTask


@luigi.util.inherits(BaseLoadingPipelineParams)
class WriteTDRMetricsFilesTask(luigi.Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_write_tdr_metrics_file_task = set()

    def complete(self) -> bool:
        return len(self.dynamic_write_tdr_metrics_file_task) >= 1 and all(
            write_tdr_metrics_file_task.complete()
            for write_tdr_metrics_file_task in self.dynamic_write_tdr_metrics_file_task
        )

    def run(self):
        for bq_table_name in gen_bq_table_names():
            self.dynamic_write_tdr_metrics_file_task.add(
                self.clone(WriteTDRMetricsFileTask, bq_table_name=bq_table_name),
            )
        yield self.dynamic_write_tdr_metrics_file_task
