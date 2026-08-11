import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.paths import relatedness_check_tsv_path
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_relatedness_check_table import (
    WriteRelatednessCheckTableTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteRelatednessCheckTsvTask(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            relatedness_check_tsv_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self):
        return [self.clone(WriteRelatednessCheckTableTask)]

    def run(self):
        ht = hl.read_table(self.input()[0].path)
        ht.export(self.output().path)
