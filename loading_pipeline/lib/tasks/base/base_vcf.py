from typing import ClassVar

import luigi
import luigi.format

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.files import LocalizableTarget


class BaseVCFTask(luigi.Task):
    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = []
    INFO_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {}
    FORMAT_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {}

    def output(self) -> list[LocalizableTarget]:
        vcf_path = self.vcf_path()
        return [
            LocalizableTarget(
                vcf_path,
                format=luigi.format.UTF8 >> luigi.format.Gzip,
            ),
            LocalizableTarget(f'{vcf_path}.tbi'),
        ]

    def run(self) -> None:
        self.output()[0].makedirs()
        targets = self.prepare_vcf_inputs()
        self.generate_vcf(targets)

        for target in self.output():
            target.persist()

    def vcf_path(self) -> str:
        raise NotImplementedError

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        return []

    def generate_vcf(self, targets: list[luigi.LocalTarget]) -> None:
        self.run_bcftools(self.OUTPUT_COMMAND_ARGS, self.output()[0], targets)

    @staticmethod
    def run_bcftools(
        command_args: list[str],
        output_target: luigi.LocalTarget,
        input_targets: list[luigi.LocalTarget],
        output_type: str | None = 'z',
        plugin_options: list[str] | None = None,
    ) -> None:
        run_command(
            [
                'bcftools',
                *command_args,
                *([f'-O{output_type}'] if output_type else []),
                '-o',
                output_target.path,
                *[target.path for target in input_targets],
                *(plugin_options or []),
            ],
        )
        if output_type != 'u':
            run_command(['tabix', '-f', '-p', 'vcf', output_target.path])

    def format_vcf_header(
        self,
        sample_ids: list[str],
        additional_rows: list[str],
    ) -> str:
        header = [
            '##fileformat=VCFv4.2',
            *additional_rows,
            *(
                f'##INFO=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in self.INFO_FIELDS.items()
            ),
            *(
                f'##FORMAT=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in self.FORMAT_FIELDS.items()
            ),
            '\t'.join(
                [
                    '#CHROM',
                    'POS',
                    'ID',
                    'REF',
                    'ALT',
                    'QUAL',
                    'FILTER',
                    'INFO',
                    'FORMAT',
                    *sample_ids,
                ],
            ),
        ]

        header_content = '\n'.join(header)
        return f'{header_content}\n'

    @staticmethod
    def find_vcf_header_line(vcf_target: luigi.LocalTarget, header_prefix: str) -> str:
        with vcf_target.open() as f:
            for line in f:
                if line.startswith(header_prefix):
                    return line
                if not line.startswith('#'):
                    break
        return ''
