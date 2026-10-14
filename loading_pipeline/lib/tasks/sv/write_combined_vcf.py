import json

import luigi
import luigi.util

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.paths import (
    imported_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_vcf import (
    BaseVCFTask,
)
from loading_pipeline.lib.tasks.sv.single_sample_vcf import (
    SingleSampleVCFTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteCombinedSvVcf(BaseVCFTask):
    def complete(self) -> bool:
        if not super().complete():
            return False
        if not self.input()[0].exists():
            return False

        samples = None
        self.output()[0].localize()
        with self.output()[0].open() as f:
            for line in f:
                if line.startswith('#CHROM'):
                    samples = set(line.split('FORMAT', 1)[-1].strip().split())
                    break
                if not line.startswith('#'):
                    break

        expected_samples, _ = self._sample_ids()
        return samples == set(expected_samples)

    def vcf_name(self) -> str:
        return imported_callset_path(
            self.reference_genome,
            self.dataset_type,
            self.callset_path,
        ).replace('.mt', '.vcf.gz')

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
        ]

    def write_vcf(self) -> None:
        out_path = self.output()[0].path
        sample_ids, male_sample_ids = self._sample_ids()
        sample_file_tasks = [
            SingleSampleVCFTask(
                path_template=self.callset_path,
                out_path=(self.output()[0].remote_path or out_path).rsplit('/', 1)[0],
                sample_id=sample_id,
                vcf_sample_id=vcf_sample_id,
                is_male=sample_id in male_sample_ids,
            )
            for sample_id, vcf_sample_id in sample_ids.items()
        ]
        yield sample_file_tasks

        for task in sample_file_tasks:
            for target in task.output():
                target.localize()

        vcf_paths = [task.output()[0].path for task in sample_file_tasks]
        self.output()[0].makedirs()
        run_command(
            [
                'bcftools',
                'merge',
                '-m',
                'none',
                '--missing-to-ref',
                '-Oz',
                '-o',
                out_path,
                *vcf_paths,
            ],
        )
        run_command(['tabix', '-f', '-p', 'vcf', out_path])

    def _sample_ids(self) -> tuple[dict[str, str], list[str]]:
        with self.input()[0].open() as f:
            metadata_json = json.load(f)

        return {
            sample_id: metadata_json['remap_ids'].get(sample_id)
            for samples in metadata_json['family_samples'].values()
            for sample_id in samples
        }, metadata_json['male_sample_ids']
