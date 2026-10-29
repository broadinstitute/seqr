import random
from typing import ClassVar

import luigi
import luigi.format

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

    INFO_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'ALGORITHMS': ('.', 'String'),
        'BOTHSIDES_SUPPORT': ('0', 'Flag'),
        'CHR2': ('1', 'String'),
        'CPX_INTERVALS': ('.', 'String'),
        'CPX_TYPE': ('1', 'String'),
        'END': ('1', 'Integer'),
        'END2': ('1', 'Integer'),
        'SVLEN': ('1', 'Integer'),
        'SVTYPE': ('1', 'String'),
        'StrVCTVRE': ('1', 'String'),
        'GNOMAD_V4.1_TRUTH_VID': ('1', 'String'),
        'SEQR_INTERNAL_TRUTH_VID': ('1', 'String'),
        'PREDICTED_BREAKEND_EXONIC': ('.', 'String'),
        'PREDICTED_COPY_GAIN': ('.', 'String'),
        'PREDICTED_DUP_PARTIAL': ('.', 'String'),
        'PREDICTED_INTRAGENIC_EXON_DUP': ('.', 'String'),
        'PREDICTED_INTRONIC': ('.', 'String'),
        'PREDICTED_INV_SPAN': ('.', 'String'),
        'PREDICTED_LOF': ('.', 'String'),
        'PREDICTED_MSV_EXON_OVERLAP': ('.', 'String'),
        'PREDICTED_NEAREST_TSS': ('.', 'String'),
        'PREDICTED_PARTIAL_EXON_DUP': ('.', 'String'),
        'PREDICTED_PROMOTER': ('.', 'String'),
        'PREDICTED_TSS_DUP': ('.', 'String'),
        'PREDICTED_UTR': ('.', 'String'),
    }

    FORMAT_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'GT': ('1', 'String'),
        'GQ': ('1', 'Integer'),
        'RD_CN': ('1', 'Integer'),
        'CONC_ST': ('.', 'String'),
    }

    KEEP_FIELDS: ClassVar[str] = ','.join(
        [
            *(f'^INFO/{field}' for field in INFO_FIELDS),
            *(f'^FORMAT/{field}' for field in FORMAT_FIELDS),
        ],
    )

    def requires(self) -> list[luigi.Task]:
        pathname = self.path_template.replace('*', self.vcf_sample_id or self.sample_id)
        return [
            LocalizableFileTask(pathname),
            LocalizableFileTask(f'{pathname}.tbi'),
        ]

    def vcf_path(self) -> str:
        file_id = (
            f'{self.vcf_sample_id}__{self.sample_id}'
            if self.vcf_sample_id
            else self.sample_id
        )
        if self.is_male:
            file_id = f'{file_id}.male'
        return f'{self.output_dir}/{file_id}.norm.vcf.gz'

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        for target in self.input():
            target.localize()

        reformatted_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            [
                'view',
                '--regions',
                ','.join(CONTIGS),
            ],
            reformatted_target,
            self.input()[:1],
            output_type='u',
        )

        if self.is_male:
            haploid_target = luigi.LocalTarget(is_tmp=True)
            self.run_bcftools(
                ['+setGT'],
                haploid_target,
                [reformatted_target],
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
            reformatted_target = haploid_target

        annotated_target = luigi.LocalTarget(is_tmp=True)
        rand_id = random.randint(1e5, 1e6 - 1)  # noqa: S311 # nosec
        self.run_bcftools(
            [
                'annotate',
                '-x',
                self.KEEP_FIELDS,
                '--set-id',
                f'%ID-{rand_id}',
            ],
            annotated_target,
            [reformatted_target],
        )

        header_target = self._write_header(self.input()[0])
        return [header_target, annotated_target]

    def generate_vcf(self, targets: list[luigi.LocalTarget]) -> None:
        self.run_bcftools(
            ['reheader', '-h', targets[0].path],
            self.output()[0],
            targets[1:],
            output_type=None,
        )

    def _write_header(self, vcf_target: LocalizableTarget) -> luigi.LocalTarget:
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

        header_target = luigi.LocalTarget(is_tmp=True)
        with header_target.open('w') as f:
            f.write(self.format_vcf_header([self.sample_id], header_rows))

        return header_target
