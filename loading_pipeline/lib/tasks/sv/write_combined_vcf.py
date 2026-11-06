import json
from typing import ClassVar

import luigi
import luigi.util

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
    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = ['merge', '-m', 'id']

    def complete(self) -> bool:
        if not super().complete():
            return False
        if not self.input()[0].exists():
            return False

        self.output()[0].localize()
        header_line = self.find_vcf_header_line(self.output()[0], '#CHROM')
        samples = set(header_line.split('FORMAT', 1)[-1].strip().split())
        expected_samples, _ = self._sample_ids()
        return samples == set(expected_samples)

    def output_dir(self) -> str:
        return imported_callset_path(
            self.reference_genome,
            self.dataset_type,
            self.callset_path,
        ).removesuffix('.mt')

    def vcf_path(self) -> str:
        return f'{self.output_dir()}/combined.vcf.gz'

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
        ]

    def run(self) -> None:
        self.output()[0].makedirs()
        yield self._sample_file_tasks()
        super().run()

    def _sample_file_tasks(self) -> list[SingleSampleVCFTask]:
        sample_ids, male_sample_ids = self._sample_ids()
        output_dir = self.output_dir()
        return [
            SingleSampleVCFTask(
                path_template=self.callset_path,
                output_dir=output_dir,
                sample_id=sample_id,
                vcf_sample_id=vcf_sample_id,
                is_male=sample_id in male_sample_ids,
            )
            for sample_id, vcf_sample_id in sample_ids.items()
        ]

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        sample_file_tasks = self._sample_file_tasks()
        for task in sample_file_tasks:
            for target in task.output():
                target.localize()

        return [task.output()[0] for task in sample_file_tasks]

    def _sample_ids(self) -> tuple[dict[str, str], list[str]]:
        with self.input()[0].open() as f:
            metadata_json = json.load(f)

        return {
            sample_id: metadata_json['remap_ids'].get(sample_id)
            for samples in metadata_json['family_samples'].values()
            for sample_id in samples
        }, metadata_json['male_sample_ids']
