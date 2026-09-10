import luigi

from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc import (
    BaseRunJobOnDataprocTask,
)
from loading_pipeline.lib.tasks.run_pipeline import RunPipelineTask


@luigi.util.inherits(BaseLoadingRunParams)
class RunPipelineOnDataprocTask(BaseRunJobOnDataprocTask):
    @property
    def task(self) -> luigi.Task:
        return RunPipelineTask
