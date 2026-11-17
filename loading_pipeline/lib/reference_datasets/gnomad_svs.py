import luigi
import pandas as pd

from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)


def get_df(input_target: luigi.Target) -> pd.DataFrame:
    df = BaseWriteParquetFromVcfTask.import_vcf(input_target)
    fields = {'af': 'AF', 'het': 'N_HET', 'hom': 'N_HOMALT'}
    for field, raw_field in fields.items():
        df[field] = df[raw_field].astype(float)
    return df[['ID', *fields.keys()]].rename(columns={'ID': 'id'})
