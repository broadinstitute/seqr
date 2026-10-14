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


class SingleSampleVCFTask(luigi.Task):
    path_template = luigi.Parameter()
    out_path = luigi.Parameter()
    sample_id = luigi.Parameter()
    vcf_sample_id = luigi.Parameter(default=None)

    def requires(self) -> list[luigi.Task]:
        pathname = self.path_template.replace('*', self.vcf_sample_id or self.sample_id)
        return [
            LocalizableFileTask(
                pathname,
                format=luigi.format.UTF8 >> luigi.format.Gzip,
            ),
            LocalizableFileTask(f'{pathname}.tbi'),
        ]

    def output(self) -> list[LocalizableTarget]:
        file_id = (
            f'{self.vcf_sample_id}__{self.sample_id}'
            if self.vcf_sample_id
            else self.sample_id
        )
        out_path = f'{self.out_path}{file_id}.norm.vcf.gz'
        return [
            LocalizableTarget(out_path),
            LocalizableTarget(f'{out_path}.tbi'),
        ]

    def run(self) -> None:
        for target in self.input():
            target.localize()

        contig_filtered_target = luigi.LocalTarget(is_tmp=True)
        run_command(
            [
                'bcftools',
                'view',
                '-t',
                ','.join(CONTIGS),
                '-Ou',
                '-o',
                contig_filtered_target.path,
                self.input()[0].path,
            ],
        )

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
                contig_filtered_target.path,
            ],
        )

        header_path = self._write_header(self.input()[0])
        out_path = self.output()[0].path
        run_command(
            [
                'bcftools',
                'reheader',
                '-h',
                header_path,
                '-o',
                out_path,
                annotated_target.path,
            ],
        )
        run_command(['tabix', '-f', '-p', 'vcf', out_path])

        for target in self.output():
            target.persist()

    def _write_header(self, vcf_target: LocalizableTarget) -> str:
        filter_lines = []
        with vcf_target.open() as f:
            for line in f:
                if not line.startswith('##'):
                    break
                if line.startswith('##FILTER=<'):
                    filter_lines.append(line.rstrip('\n'))

        header_target = luigi.LocalTarget(is_tmp=True)
        header = '\n'.join(
            [
                '##fileformat=VCFv4.2',
                *filter_lines,
                *(
                    f'##INFO=<ID={field},Number={number},Type={field_type},Description="{field}">'
                    for field, (number, field_type) in INFO_FIELDS.items()
                ),
                *(
                    f'##FORMAT=<ID={field},Number={number},Type={field_type},Description="{field}">'
                    for field, (number, field_type) in FORMAT_FIELDS.items()
                ),
                *(f'##contig=<ID={contig}>' for contig in CONTIGS),
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
                        self.sample_id,
                    ],
                ),
            ],
        )
        with header_target.open('w') as f:
            f.write(f"{header}\n")

        return header_target.path
