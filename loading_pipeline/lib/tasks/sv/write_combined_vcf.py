import json
import subprocess  # nosec B404

import luigi
import luigi.format
import luigi.util

from loading_pipeline.lib.paths import (
    imported_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteCombinedSvVcf(luigi.Task):
    def complete(self) -> bool:
        if not super().complete():
            return False
        if not self.input()[0].exists():
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
            ).replace('.mt', '.vcf.gz'),
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
        out_path = self.output().path
        bcftools_cmd = ['bcftools', 'merge', '-m', 'none', '-Oz', '-o', out_path]
        tabix_cmd = ['tabix', '-f', '-p', 'vcf', out_path]
        try:
            subprocess.run(bcftools_cmd + vcf_paths, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
            subprocess.run(tabix_cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
        except subprocess.CalledProcessError as e:
            e.add_note(e.stderr)
            raise

    def _sample_ids(self) -> set[str]:
        with open(self.input()[0].path) as f:
            metadata_json = json.load(f)

        return {
            sample_id
            for samples in metadata_json['family_samples'].values()
            for sample_id in samples
        }
