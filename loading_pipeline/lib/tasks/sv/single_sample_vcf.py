import random
from typing import ClassVar

import luigi
import luigi.format
import pandas as pd

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.tasks.base.base_vcf import (
    BaseVCFTask,
)
from loading_pipeline.lib.tasks.files import LocalizableFileTask, LocalizableTarget

CONTIGS = list(ReferenceGenome.GRCh38.contig_recoding().values())

PAR1_END = 2781479
PAR2_START = 155701383


class SingleSampleVCFTask(BaseVCFTask):
    path_template = luigi.Parameter()
    output_dir = luigi.Parameter()
    sample_id = luigi.Parameter()
    is_male = luigi.BoolParameter()
    vcf_sample_id = luigi.OptionalParameter(default=None)

    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = ['concat']

    def requires(self) -> list[luigi.Task]:
        sample_id = self.vcf_sample_id or self.sample_id
        return [
            SingleSampleSvVCFTask(
                pathname=self.path_template.replace('*', f'{sample_id}.sv'),
                output_filename=self.output_filename(),
                sample_id=self.sample_id,
                is_male=self.is_male
            ),
        ]

    def output_filename(self) -> str:
        file_id = (
            f'{self.vcf_sample_id}__{self.sample_id}'
            if self.vcf_sample_id
            else self.sample_id
        )
        return f'{self.output_dir}/{file_id}'

    def vcf_path(self) -> str:
        output_filename = self.output_filename()
        if self.is_male:
            output_filename = f'{output_filename}.male'
        return f'{output_filename}.norm.vcf.gz'

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        return self.input()


class SingleSampleSvVCFTask(BaseVCFTask):
    pathname = luigi.Parameter()
    output_filename = luigi.Parameter()
    sample_id = luigi.Parameter()
    is_male = luigi.BoolParameter()

    INFO_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'CHR2': ('1', 'String'),
        'CPX_INTERVALS': ('.', 'String'),
        'CPX_TYPE': ('1', 'String'),
        'END': ('1', 'Integer'),
        'END2': ('1', 'Integer'),
        'SVLEN': ('1', 'Integer'),
        'SVTYPE': ('1', 'String'),
    }

    FORMAT_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'GT': ('1', 'String'),
        'GQ': ('1', 'Integer'),
        'RD_CN': ('1', 'Integer'),
    }

    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = [
        'view',
        '--regions',
        ','.join(CONTIGS),
    ]

    def requires(self) -> list[luigi.Task]:
        return [
            LocalizableFileTask(self.pathname),
            LocalizableFileTask(f'{self.pathname}.tbi'),
        ]

    def vcf_path(self) -> str:
        suffix = 'sv_norm'
        if self.is_male:
            suffix = f'male.{suffix}'
        return f'{self.output_filename}.{suffix}.vcf.gz'

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        for target in self.input():
            target.localize()

        vcf_target = self.preprocess_vcf(self.input()[0])
        df = self.import_vcf(vcf_target)
        df = self.process_vcf_df(df)

        header_rows = self._get_header_rows(self.input()[0])
        return [self.export_vcf(df, [self.sample_id], header_rows)]

    def preprocess_vcf(self, input_target: luigi.LocalTarget) -> luigi.LocalTarget:
        if self.is_male:
            haploid_target = luigi.LocalTarget(is_tmp=True)
            self.run_bcftools(
                ['+setGT'],
                haploid_target,
                [input_target],
                output_type='u',
                plugin_options=[
                    '--',
                    '--target-gt',
                    'q',
                    '--new-gt',
                    'c:1',
                    '--include',
                    f'CHROM="chrY" || (CHROM="chrX" && ((POS>{PAR1_END} && POS<{PAR2_START}) || (POS<={PAR1_END} && INFO/END>{PAR1_END})))',
                ],
            )
            input_target = haploid_target

        annotated_target = luigi.LocalTarget(is_tmp=True)
        rand_id = random.randint(10_000_000, 99_999_999)  # noqa: S311 # nosec
        self.run_bcftools(
            [
                'annotate',
                '-x',
                ','.join(
                    [
                        *(f'^INFO/{field}' for field in self.INFO_FIELDS),
                        *(f'^FORMAT/{field}' for field in self.FORMAT_FIELDS),
                    ],
                ),
                '--set-id',
                f'%ID-{rand_id}',
            ],
            annotated_target,
            [input_target],
            output_type='v',
        )
        return annotated_target

    @staticmethod
    def process_vcf_df(df: pd.DataFrame) -> pd.DataFrame:
        # TODO process, format info fields back?
        return df

    @staticmethod
    def _get_header_rows(vcf_target: LocalizableTarget) -> list[str]:
        header_rows = []
        vcf_target.format = luigi.format.UTF8 >> luigi.format.Gzip
        with vcf_target.open() as f:
            for line in f:
                if not line.startswith('##'):
                    break
                if line.startswith('##FILTER=<'):
                    header_rows.append(line.rstrip('\n'))
                elif line.startswith('##contig=<'):
                    contig_id = (
                        line.removeprefix('##contig=<ID=').split(',')[0].split('>')[0]
                    )
                    if contig_id in CONTIGS:
                        header_rows.append(line.rstrip('\n'))

        return header_rows
