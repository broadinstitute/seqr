import luigi
import luigi.format

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.files import LocalizableTarget


class BaseVCFTask(luigi.Task):
    INFO_FIELDS = {}
    FORMAT_FIELDS = {}

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
        targets = self.prepare_vcf_inputs()
        command = self.generate_vcf_command(targets)
        run_command(command)
        run_command(['tabix', '-f', '-p', 'vcf', self.output()[0].path])

        for target in self.output():
            target.persist()

    def vcf_path(self) -> str:
        raise NotImplementedError

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        return []

    def generate_vcf_command(self, targets: list[luigi.LocalTarget]) -> list[str]:
        raise NotImplementedError

    def format_vcf_header(self, sample_ids: list[str], additional_rows: list[str] | None = None) -> str:
        columns = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO']
        if sample_ids:
            columns = [*columns, 'FORMAT', *sample_ids]
        header = [
            '##fileformat=VCFv4.2',
            *(
                f'##INFO=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in self.INFO_FIELDS.items()
            ),
            *(
                f'##FORMAT=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in self.FORMAT_FIELDS.items()
            ),
            *(additional_rows or []),
            '\t'.join(columns),
        ]

        header_content = '\n'.join(header)
        return f'{header_content}\n'
