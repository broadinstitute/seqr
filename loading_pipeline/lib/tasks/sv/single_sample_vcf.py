import luigi
import luigi.format

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.files import LocalizableFileTask, LocalizableTarget

CONTIGS = list(ReferenceGenome.GRCh38.contig_recoding().values())

INFO_FIELDS = {
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

FORMAT_FIELDS = {
    'GT': ('1', 'String'),
    'GQ': ('1', 'Integer'),
    'RD_CN': ('1', 'Integer'),
    'CONC_ST': ('.', 'String'),
}

KEEP_FIELDS = ','.join(
    [
        *(f'^INFO/{field}' for field in INFO_FIELDS),
        *(f'^FORMAT/{field}' for field in FORMAT_FIELDS),
    ],
)

PAR1_END = 2781479
PAR2_START = 155701383


class SingleSampleVCFTask(luigi.Task):
    path_template = luigi.Parameter()
    out_path = luigi.Parameter()
    sample_id = luigi.Parameter()
    is_male = luigi.BoolParameter()
    vcf_sample_id = luigi.OptionalParameter(default=None)

    def requires(self) -> list[luigi.Task]:
        pathname = self.path_template.replace('*', self.vcf_sample_id or self.sample_id)
        return [
            LocalizableFileTask(pathname),
            LocalizableFileTask(f'{pathname}.tbi'),
        ]

    def output(self) -> list[LocalizableTarget]:
        file_id = (
            f'{self.vcf_sample_id}__{self.sample_id}'
            if self.vcf_sample_id
            else self.sample_id
        )
        if self.is_male:
            file_id = f'{file_id}.male'
        out_path = f'{self.out_path}{file_id}.norm.vcf.gz'
        return [
            LocalizableTarget(out_path),
            LocalizableTarget(f'{out_path}.tbi'),
        ]

    def run(self) -> None:
        for target in self.input():
            target.localize()

        reformatted_target = luigi.LocalTarget(is_tmp=True)
        run_command(
            [
                'bcftools',
                'view',
                '--regions',
                ','.join(CONTIGS),
                '-Ou',
                '-o',
                reformatted_target.path,
                self.input()[0].path,
            ],
        )

        if self.is_male:
            haploid_target = luigi.LocalTarget(is_tmp=True)
            run_command(
                [
                    'bcftools',
                    '+setGT',
                    '-Ou',
                    '-o',
                    haploid_target.path,
                    reformatted_target.path,
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
        run_command(
            [
                'bcftools',
                'annotate',
                '-x',
                KEEP_FIELDS,
                '-Oz',
                '-o',
                annotated_target.path,
                reformatted_target.path,
            ],
        )

        header_target = self._write_header(self.input()[0])
        out_path = self.output()[0].path
        run_command(
            [
                'bcftools',
                'reheader',
                '-h',
                header_target.path,
                '-o',
                out_path,
                annotated_target.path,
            ],
        )
        run_command(['tabix', '-f', '-p', 'vcf', out_path])

        for target in self.output():
            target.persist()

    def _write_header(self, vcf_target: LocalizableTarget) -> luigi.LocalTarget:
        header = ['##fileformat=VCFv4.2']
        vcf_target.format = luigi.format.UTF8 >> luigi.format.Gzip
        with vcf_target.open() as f:
            for line in f:
                if not line.startswith('##'):
                    break
                if line.startswith('##FILTER=<'):
                    header.append(line.rstrip('\n'))
                elif line.startswith('##contig=<'):
                    contig_id = (
                        line.removeprefix('##contig=<ID=').split(',')[0].split('>')[0]
                    )
                    if contig_id in CONTIGS:
                        header.append(line.rstrip('\n'))

        header = [
            *header,
            *(
                f'##INFO=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in INFO_FIELDS.items()
            ),
            *(
                f'##FORMAT=<ID={field},Number={number},Type={field_type},Description="{field}">'
                for field, (number, field_type) in FORMAT_FIELDS.items()
            ),
            f'#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{self.sample_id}',
        ]
        header_target = luigi.LocalTarget(is_tmp=True)
        with header_target.open('w') as f:
            header_content = '\n'.join(header)
            f.write(f'{header_content}\n')

        return header_target
