import pandas as pd


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    fields = {'END': 'END', 'SVLEN': 'SVLEN', 'af': 'AF', 'het': 'N_HET', 'hom': 'N_HOMALT'}
    for field, raw_field in fields.items():
        df[field] = df[raw_field].astype(float)
    return df[['ID', '#CHROM', 'POS', 'SVTYPE', *fields.keys()]]
