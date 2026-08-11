import luigi
import luigi.util

from loading_pipeline.lib.core.feature_flag import FeatureFlag
from loading_pipeline.lib.paths import pipeline_run_success_file_path
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.dataproc.run_pipeline_on_dataproc import (
    RunPipelineOnDataprocTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.run_pipeline import RunPipelineTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteSuccessFileTask(luigi.Task):
    attempt_id = luigi.IntParameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            pipeline_run_success_file_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> luigi.Task:
        return (
            self.clone(RunPipelineOnDataprocTask, attempt_id=self.attempt_id)
            if FeatureFlag.RUN_PIPELINE_ON_DATAPROC
            else self.clone(RunPipelineTask, attempt_id=self.attempt_id)
        )

    def run(self):
        with self.output().open('w') as f:
            f.write('')
