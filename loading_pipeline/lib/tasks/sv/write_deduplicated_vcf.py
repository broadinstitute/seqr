import os

import luigi
import luigi.util

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.paths import runs_path
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.sv.write_combined_vcf import (
    WriteCombinedSvVcf,
)
from loading_pipeline.lib.tasks.sv.write_existing_variants_vcf import (
    WriteExistingVariantsVcfTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteDeduplicatedSvVcfTask(BaseVCFTask):
    def complete(self) -> bool:
        if not super().complete():
            return False

        # Ensure input VCF has the correct samples for the current run
        return self.requires()[0].complete()

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteCombinedSvVcf),
            self.clone(WriteExistingVariantsVcfTask),
        ]

    def vcf_path(self) -> str:
        return os.path.join(
            runs_path(
                self.reference_genome,
                self.dataset_type,
            ),
            self.run_id,
            'deduplicated.vcf.gz',
        )

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        for target in self.input():
            target.localize()

        existing_merged_target = luigi.LocalTarget(is_tmp=True)
        run_command(
            [
                'bcftools',
                'merge',
                '-m',
                'none',
                '-Ou',
                '-o',
                existing_merged_target.path,
                self.input()[1].path,
                self.input()[0].path,
            ],
        )

        return []

    def generate_vcf_command(self, targets: list[luigi.LocalTarget]) -> list[str]:
        return [
            'bcftools',
            'merge',
            '-m',
            'none',
            '-Oz',
            '-o',
            self.output()[0].path,
            *[target.path for target in targets],
        ]

