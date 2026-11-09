import os

import luigi
import pandas as pd

from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget


class BaseWriteParquetFromVcfTask(BaseVCFTask):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            os.path.join(
                self.output_dir(),
                'part-0.parquet',
            ),
        )

    def output_dir(self) -> str:
        return ''

    def run(self) -> None:
        targets = (
            self.input()[0] if isinstance(self.input()[0], list) else [self.input()[0]]
        )
        for target in targets:
            target.localize()

        df = self.create_data_frame()

        output = self.output()
        output.format = luigi.format.Nop
        with output.open('w') as f:
            df.to_parquet(f)

    def create_data_frame(self) -> pd.DataFrame:
        raise NotImplementedError

    @staticmethod
    def import_vcf(input_target: luigi.Target) -> pd.DataFrame:
        if input_target.path.endswith('.gz'):
            input_target.format = luigi.format.UTF8 >> luigi.format.Gzip
        with input_target.open() as f:
            num_header_rows = next(
                i for i, line in enumerate(f) if not line.startswith('##')
            )
        df = pd.read_csv(input_target.path, sep='\t', skiprows=num_header_rows)

        info = pd.DataFrame(
            [
                dict(
                    field.split('=', 1) if '=' in field else (field, True)
                    for field in entry.split(';')
                )
                for entry in df.pop('INFO')
            ],
            index=df.index,
        )
        return df.join(info)
