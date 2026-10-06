import json
import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    imported_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteMergedSvVcf(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ).replace('.mt', '.merged.vcf.gz'),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
        ]

    def run(self) -> None:
        with open(self.input()[0].path) as f:
            metadata_json = json.load(f)

        sample_file_tasks = [
            RawFileTask(self.callset_path.replace('*', sample_id))
            for samples in metadata_json['family_samples'].values() for sample_id in samples
        ]
        yield sample_file_tasks

        vcf_paths = [task.output().path for task in sample_file_tasks]
        out_file = self.output().path
