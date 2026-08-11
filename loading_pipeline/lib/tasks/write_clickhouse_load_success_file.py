import json

import hailtop.fs as hfs
import luigi
import luigi.util

from loading_pipeline.lib.misc.clickhouse import (
    load_complete_run,
)
from loading_pipeline.lib.paths import (
    clickhouse_load_success_file_path,
    metadata_for_run_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_success_file import WriteSuccessFileTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteClickhouseLoadSuccessFileTask(luigi.Task):
    attempt_id = luigi.IntParameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            clickhouse_load_success_file_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> luigi.Task:
        return self.clone(WriteSuccessFileTask)

    def run(self):
        with hfs.open(
            metadata_for_run_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        ) as f:
            family_guids = list(json.load(f)['family_samples'].keys())
        load_complete_run(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
            # Note: nasty bug here where Luigi parses ListParameters to tuples.
            list(self.project_guids),
            family_guids,
        )

        with self.output().open('w') as f:
            f.write('')
