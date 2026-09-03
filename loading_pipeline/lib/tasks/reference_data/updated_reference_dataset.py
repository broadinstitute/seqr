import luigi

from loading_pipeline.lib.paths import valid_reference_dataset_path
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget


@luigi.util.inherits(BaseLoadingPipelineParams)
class UpdatedReferenceDatasetTask(BaseWriteTask):
    reference_dataset: ReferenceDataset = luigi.EnumParameter(
        enum=ReferenceDataset,
    )

    def output(self):
        return GCSorLocalTarget(
            valid_reference_dataset_path(
                self.reference_genome,
                self.reference_dataset,
            ),
        )

    def create_table(self):
        return self.reference_dataset.get_ht(self.reference_genome)
