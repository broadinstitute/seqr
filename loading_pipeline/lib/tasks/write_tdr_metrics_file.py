import csv

import google.api_core.exceptions
import luigi
import luigi.util

from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.terra_data_repository import (
    BIGQUERY_METRICS,
    bq_metrics_query,
)
from loading_pipeline.lib.paths import tdr_metrics_path
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget

logger = get_logger(__name__)


@luigi.util.inherits(BaseLoadingPipelineParams)
class WriteTDRMetricsFileTask(luigi.Task):
    bq_table_name = luigi.Parameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            tdr_metrics_path(
                self.reference_genome,
                self.dataset_type,
                self.bq_table_name,
            ),
        )

    def run(self):
        with self.output().open('w') as f:
            writer = csv.DictWriter(f, fieldnames=BIGQUERY_METRICS, delimiter='\t')
            writer.writeheader()
            try:
                for row in bq_metrics_query(self.bq_table_name):
                    writer.writerow(row)
            except google.api_core.exceptions.BadRequest:
                logger.exception('Query Failed')
