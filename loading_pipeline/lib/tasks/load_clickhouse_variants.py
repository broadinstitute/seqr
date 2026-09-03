import luigi
import luigi.util

from loading_pipeline.lib.misc.clickhouse import (
    load_run_variants,
)
from loading_pipeline.lib.paths import (
    clickhouse_load_success_file_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_success_file import WriteSuccessFileTask


@luigi.util.inherits(BaseLoadingRunParams)
class LoadClickhouseVariants(luigi.Task):
    attempt_id = luigi.IntParameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            clickhouse_load_success_file_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ).replace('_CLICKHOUSE_LOAD_SUCCESS', '_CLICKHOUSE_LOAD_VARIANTS_SUCCESS'),
        )

    def requires(self) -> luigi.Task:
        return self.clone(WriteSuccessFileTask)

    def run(self):
        load_run_variants(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        )

        with self.output().open('w') as f:
            f.write('')
