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
