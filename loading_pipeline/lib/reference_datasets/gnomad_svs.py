import luigi
import pandas as pd

from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)


def get_df(input_target: luigi.Target) -> pd.DataFrame:
    df = BaseWriteParquetFromVcfTask.import_vcf(input_target)
    fields = {
        'END': 'END',
        'SVLEN': 'SVLEN',
        'af': 'AF',
        'ac': 'AC',
        'an': 'AN',
        'het': 'N_HET',
        'hom': 'N_HOMALT',
    }
    for field, raw_field in fields.items():
        df[field] = df[raw_field].astype(float)
    return df[['ID', '#CHROM', 'POS', 'SVTYPE', *fields.keys()]]
