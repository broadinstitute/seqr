import luigi

from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget


class BaseWriteParquetFromVcfTask(BaseVCFTask):
    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def run(self) -> None:
        for target in self.input()[0]:
            target.localize()

        df = self.create_data_frame()

        parquet = self.output()
        parquet.format = luigi.format.Nop
        with parquet.open('w') as f:
            df.to_parquet(f)
