import luigi
import pandas as pd


def get_df(input_target: luigi.Target) -> pd.DataFrame:
    input_target.format = luigi.format.Nop
    with input_target.open() as f:
        return pd.read_parquet(f)
