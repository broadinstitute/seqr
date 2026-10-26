from typing import ClassVar

import luigi
import luigi.format
import luigi.util
import pandas as pd

from loading_pipeline.lib.paths import existing_variants_parquet_path
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_vcf import (
    BaseVCFTask,
)
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteExistingVariantsVcfTask(BaseVCFTask):
    OUTPUT_COMMAND_ARGS: ClassVar[list[str]] = ['view']

    INFO_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'CHR2': ('1', 'String'),
        'END': ('1', 'Integer'),
        'SVTYPE': ('1', 'String'),
    }

    FORMAT_FIELDS: ClassVar[dict[str, tuple[str, str]]] = {
        'GT': ('1', 'String'),
    }

    def vcf_path(self) -> str:
        return existing_variants_parquet_path(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        ).replace('.parquet', '.vcf.gz')

    def requires(self) -> list[luigi.Task]:
        return [self.clone(WriteExistingVariantsParquetTask)]

    def prepare_vcf_inputs(self) -> list[luigi.LocalTarget]:
        parquet = self.input()[0]
        parquet.format = luigi.format.Nop
        with parquet.open() as f:
            df = pd.read_parquet(f)
        for col in ['chrom', 'endChrom', 'svType']:
            df[col] = df[col].str.decode('utf-8')

        sv_len = df['end'] - df['pos']
        info = 'SVTYPE=' + df['svType']  + ';SVLEN=' + sv_len.astype(str) + ';END=' + df['end'].astype(str)
        has_end_chrom = df['endChrom'].notna()
        info[has_end_chrom] += ';CHR2=chr' + df.loc[has_end_chrom, 'endChrom']
        vcf_df = pd.DataFrame(
            {
                'CHROM': 'chr' + df['chrom'],
                'POS': df['pos'],
                'ID': df['variant_id'],
                'REF': 'N',
                'ALT': '<' + df['svType'] + '>',
                'QUAL': '.',
                'FILTER': '.',
                'INFO': info,
                'FORMAT': 'GT',
                'seqr_existing': '1',
            },
        ).sort_values(['CHROM', 'POS'])

        max_key = df['key_'].max() if len(df) else 0
        header = self.format_vcf_header(['seqr_existing'], [f'##maxKey={max_key}'])

        vcf_target = luigi.LocalTarget(is_tmp=True, format=luigi.format.Nop)
        with vcf_target.open('w') as f:
            f.write(header.encode())
            vcf_df.to_csv(f, sep='\t', header=False, index=False)

        return [vcf_target]
