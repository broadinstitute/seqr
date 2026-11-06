import pandas as pd


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    fields = {'af': 'AF', 'het': 'N_HET', 'hom': 'N_HOM'}
    for field, raw_field in fields.items():
        df[field] = df[raw_field].astype(float)
    return  df[['id', *fields.keys()]].rename(columns={'ID': 'id'})
