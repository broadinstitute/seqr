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

TRUVARI_PARAMS = {
    'DEL': ['--pctseq', '0.5', '--pctsize', '0.5', '--pctovl', '0.1'],
    'DUP': ['--pctseq', '0.5', '--pctsize', '0.5', '--dup-to-ins'],
    'INS': ['--pctseq', '0', '--pctsize', '0.1', '--pctovl', '0', '--dup-to-ins'],
}
TRUVARI_PARAMS['INV'] = TRUVARI_PARAMS['DEL']
TRUVARI_REFDIST = {
    'INS': 100,
}
SIZE_SPLIT_BP = 5000


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
                '-Oz',
                '-o',
                existing_merged_target.path,
                self.input()[1].path,
                self.input()[0].path,
                '--write-index=tbi',
            ],
        )

        tuned_svtypes = '|'.join(TRUVARI_PARAMS)
        targets = self._run_truvari_subset(
            existing_merged_target.path,
            f'INFO/SVTYPE!~"^({tuned_svtypes})$"',
            [],
        )

        for sv_type, flags in TRUVARI_PARAMS:
            size_refdists = (
                [(None, TRUVARI_REFDIST[sv_type])]
                if sv_type in TRUVARI_REFDIST
                else [
                    ('<=', 10000),
                    ('>', 20000),
                ],
            )
            for op, refdist in size_refdists:
                size_filter = f' && abs(INFO/SVLEN){op}{SIZE_SPLIT_BP}' if op else ''
                filter_expr = f'INFO/SVTYPE="{sv_type}"{size_filter}'
                targets += self._run_truvari_subset(
                    existing_merged_target.path,
                    filter_expr,
                    [
                        *flags,
                        '--refdist',
                        str(refdist),
                        '--sizemax',
                        '-1',
                    ],
                )

        return targets

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

    @staticmethod
    def _run_truvari_subset(
        input_path: str,
        filter_expr: str,
        flags: list[str],
    ) -> list[luigi.LocalTarget]:
        filtered_target = luigi.LocalTarget(is_tmp=True)
        run_command(
            [
                'bcftools',
                'view',
                '-i',
                f"'{filter_expr}'",
                '-Oz',
                '-o',
                filtered_target.path,
                input_path,
                '--write-index=tbi',
            ],
        )

        collapsed_target = luigi.LocalTarget(is_tmp=True)
        removed_target = luigi.LocalTarget(is_tmp=True)
        run_command(
            [
                'truvari',
                'collapse',
                '-i',
                filtered_target.path,
                *flags,
                '-o',
                collapsed_target.path,
                '-c',
                removed_target.path,
            ],
        )
        return [collapsed_target, removed_target]
