import luigi
import pandas as pd

from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget


class BaseWriteParquetFromVcfTask(BaseVCFTask):
    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def run(self) -> None:
        for target in self.input()[0]:
            target.localize()

        df = self.create_data_frame()

        self.output().format = luigi.format.Nop
        with self.output().open('w') as f:
            df.to_parquet(f)

    def create_data_frame(self) -> pd.DataFrame:
        raise NotImplementedError

    @staticmethod
    def import_vcf(input_target: luigi.Target) -> pd.DataFrame:
        with input_target.open() as f:
            df = pd.read_csv(f, sep='\t')

        df['INFO'] = df['INFO'].map(
            lambda entry: dict(
                field.split('=', 1) if '=' in field else (field, True)
                for field in entry.split(';')
            ),
        )
        return df

