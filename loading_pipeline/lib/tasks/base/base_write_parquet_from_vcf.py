from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask


class BaseWriteParquetFromVcfTask(BaseWriteParquetTask, BaseVCFTask):
    def run(self) -> None:
        for target in self.input()[0]:
            target.localize()
        super().run()
