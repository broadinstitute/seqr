import luigi
import pandas as pd

from loading_pipeline.lib.annotations.expression_helpers import get_expr_for_variant_id
from loading_pipeline.lib.core.dataset_type import DatasetType
from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.paths import reference_dataset_parquet
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)
from loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc import (
    BaseRunJobOnDataprocTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget, GCSorLocalTarget, LocalizableFileTask


class UpdatedReferenceDatasetParams(luigi.Task):
    reference_genome = luigi.EnumParameter(enum=ReferenceGenome)
    dataset_type = luigi.EnumParameter(enum=DatasetType)
    reference_dataset: ReferenceDataset = luigi.EnumParameter(
        enum=ReferenceDataset,
    )
    run_id = luigi.Parameter()
    attempt_id = luigi.IntParameter()


@luigi.util.inherits(UpdatedReferenceDatasetParams)
class UpdatedReferenceDatasetParquetNoHailTask(BaseWriteParquetFromVcfTask):
    def output_dir(self) -> str:
        return reference_dataset_parquet(
            self.reference_genome,
            self.reference_dataset,
        )

    def requires(self) -> list[luigi.Task]:
        return [LocalizableFileTask(self.reference_dataset.path(self.reference_genome))]

    def create_data_frame(self) -> pd.DataFrame:
        df = self.import_vcf(self.input()[0][0])
        return self.reference_dataset.format_df(df)


@luigi.util.inherits(UpdatedReferenceDatasetParams)
class UpdatedReferenceDatasetParquetTask(luigi.Task):
    def complete(self) -> luigi.Target:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def output(self):
        return GCSorLocalTarget(
            reference_dataset_parquet(
                self.reference_genome,
                self.reference_dataset,
            ),
        )

    def run(self):
        ht = self.reference_dataset.get_ht(self.reference_genome)
        ht = ht.annotate(
            variant_id=get_expr_for_variant_id(ht),
        )
        df = ht.to_spark(flatten=False)
        df.write.parquet(
            self.output().path,
            mode='overwrite',
        )


class UpdatedReferenceDatasetParquetOnDataprocTask(BaseRunJobOnDataprocTask):
    reference_genome = luigi.EnumParameter(enum=ReferenceGenome)
    dataset_type = luigi.EnumParameter(enum=DatasetType)
    reference_dataset: ReferenceDataset = luigi.EnumParameter(
        enum=ReferenceDataset,
    )

    @property
    def task(self) -> luigi.Task:
        return UpdatedReferenceDatasetParquetTask
