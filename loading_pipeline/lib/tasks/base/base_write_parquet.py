import luigi

from loading_pipeline.lib.misc.io import checkpoint
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget


class BaseWriteParquetTask(luigi.Task):
    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def run(self) -> None:
        ht = self.create_table()
        ht, _ = checkpoint(ht)
        df = ht.to_spark(flatten=False)
        df = df.withColumnRenamed('key_', 'key')
        df.write.parquet(
            self.output().path,
            mode='overwrite',
        )
