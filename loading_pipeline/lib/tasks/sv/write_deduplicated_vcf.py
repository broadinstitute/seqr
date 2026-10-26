import os
from typing import ClassVar

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
# Truvari params for DRAGEN are tuned assuming SVLEN is not a function of END for INS/ complex events
# Adjust params for complex events for now for GATK compatibility, and change back once input formats are updated
TRUVARI_PARAMS.update({
    k: ['--pctsize', '0', '--sizemin', '0', '--sizemax', '-1'] for k in ['BND', 'CPX', 'INS']
})
TRUVARI_PARAMS['INS'] += ['--pctseq', '0', '--pctovl', '0', '--dup-to-ins']
TRUVARI_REFDIST = {
    'BND': 100,
    'CPX': 100,
    'INS': 100,
}
SIZE_SPLIT_BP = 5000


@luigi.util.inherits(BaseLoadingRunParams)
class WriteDeduplicatedSvVcfTask(BaseVCFTask):
    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = ['concat', '-a']

    def complete(self) -> bool:
        if not super().complete():
            return False

        # Ensure input VCF has the correct samples for the current run
        return self.requires()[0].complete()

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteExistingVariantsVcfTask),
            self.clone(WriteCombinedSvVcf),
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
        for targets in self.input():
            for target in targets:
                target.localize()

        existing_header = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(['view', '-h'], existing_header, self.input()[0][:1])

        metadata_header = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(['view', '-h', '-G'], metadata_header, self.input()[1][:1])

        samples_header = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(['view', '-h'], samples_header, self.input()[1][:1])

        header_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['merge', '--print-header'],
            header_target,
            [metadata_header, existing_header, samples_header],
            output_type='v',
        )

        existing_merged_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['merge', '-m', 'id', '--use-header', header_target.path],
            existing_merged_target,
            [targets[0] for targets in self.input()],
        )

        targets = self._run_truvari_subset(
            existing_merged_target,
            ' && '.join(f'INFO/SVTYPE!="{sv_type}"' for sv_type in TRUVARI_PARAMS),
            [],
        )

        for sv_type, flags in TRUVARI_PARAMS.items():
            size_refdists = (
                [(None, TRUVARI_REFDIST[sv_type])]
                if sv_type in TRUVARI_REFDIST
                else [
                    ('<=', 10000),
                    ('>', 20000),
                ]
            )
            for op, refdist in size_refdists:
                size_filter = f' && abs(INFO/SVLEN){op}{SIZE_SPLIT_BP}' if op else ''
                filter_expr = f'INFO/SVTYPE="{sv_type}"{size_filter}'
                targets += self._run_truvari_subset(
                    existing_merged_target,
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

    def _run_truvari_subset(
        self,
        input_target: luigi.LocalTarget,
        filter_expr: str,
        flags: list[str],
    ) -> list[luigi.LocalTarget]:
        filtered_target = luigi.LocalTarget(is_tmp=True)
        filtered_target.path += '.vcf.gz'
        self.run_bcftools(
            ['view', '-i', filter_expr],
            filtered_target,
            [input_target],
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

        sorted_targets = []
        for target in [collapsed_target, removed_target]:
            sorted_target = luigi.LocalTarget(is_tmp=True)
            self.run_bcftools(['sort'], sorted_target, [target])
            sorted_targets.append(sorted_target)

        return sorted_targets
