import json

import luigi
import luigi.format
import luigi.util

from loading_pipeline.lib.paths import (
    imported_callset_path,
)
from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import LocalizableTarget
from loading_pipeline.lib.tasks.sv.single_sample_vcf import (
    SingleSampleVCFTask,
)
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
        self.output()[0].localize()
        with self.output()[0].open() as f:
            for line in f:
                if line.startswith('#CHROM'):
                    samples = set(line.split('FORMAT', 1)[-1].strip().split())
                    break
                if not line.startswith('#'):
                    break

        expected_samples = set(self._sample_ids())
        return samples == expected_samples

    def output(self) -> list[luigi.Target]:
        vcf_path = imported_callset_path(
            self.reference_genome,
            self.dataset_type,
            self.callset_path,
        ).replace('.mt', '.vcf.gz')
        return [
            LocalizableTarget(
                vcf_path,
                format=luigi.format.UTF8 >> luigi.format.Gzip,
            ),
            LocalizableTarget(f'{vcf_path}.tbi'),
        ]

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
        ]

    def run(self) -> None:
        sample_file_tasks = [
            SingleSampleVCFTask(
                path_template=self.callset_path,
                sample_id=sample_id,
                vcf_sample_id=vcf_sample_id,
            )
            for sample_id, vcf_sample_id in self._sample_ids().items()
        ]
        yield sample_file_tasks

        vcf_paths = [task.output()[0].path for task in sample_file_tasks]
        out_path = self.output()[0].path
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

        for target in self.output():
            target.persist()

    def _sample_ids(self) -> dict[str, str]:
        with open(self.input()[0].path) as f:
            metadata_json = json.load(f)

        return {
            sample_id: metadata_json['remap_ids'].get(sample_id)
            for samples in metadata_json['family_samples'].values()
            for sample_id in samples
        }
