import json
import luigi
import luigi.format
import luigi.util
import subprocess

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
    def complete(self) -> bool:
        if not super().complete():
            return False
        if not self.input().exists():
            return False

        samples = None
        with self.output().open() as f:
            for line in f:
                if line.startswith('#CHROM'):
                    samples = set(line.split('FORMAT', 1)[-1].strip().split())
                    break
                if not line.startswith('#'):
                    break

        expected_samples = set(self._sample_ids())
        return samples == expected_samples

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ).replace('.mt', '.merged.vcf.gz'),
            format=luigi.format.Gzip,
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
        ]

    def run(self) -> None:
        sample_file_tasks = [
            RawFileTask(self.callset_path.replace('*', sample_id))
            for sample_id in self._sample_ids()
        ]
        yield sample_file_tasks

        vcf_paths = [task.output().path for task in sample_file_tasks]
        cmd = ['bcftools', 'merge', '-m', 'none', '-Oz', '-o', self.output().path]
        subprocess.run(cmd + vcf_paths, check=True)

    def _sample_ids(self) -> set[str]:
        with open(self.input()[0].path) as f:
            metadata_json = json.load(f)

        return {
            sample_id
            for samples in metadata_json['family_samples'].values()
            for sample_id in samples
        }
