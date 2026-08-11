import hailtop.fs as hfs
import luigi
import luigi.util

from loading_pipeline.lib.core import SampleType
from loading_pipeline.lib.paths import (
    project_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.clickhouse_migration.migrate_project_to_clickhouse import (
    MigrateProjectToClickHouseTask,
)


@luigi.util.inherits(BaseLoadingPipelineParams)
class MigrateAllProjectsToClickHouseTask(luigi.WrapperTask):
    run_id = luigi.Parameter()
    attempt_id = luigi.IntParameter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parquet_tasks = set()

    def complete(self):
        return len(self.dynamic_parquet_tasks) >= 1 and all(
            dynamic_parquet_tasks.complete()
            for dynamic_parquet_tasks in self.dynamic_parquet_tasks
        )

    def run(self):
        for sample_type in SampleType:
            for p in hfs.ls(
                project_table_path(
                    self.reference_genome,
                    self.dataset_type,
                    sample_type,
                    '*',
                ),
            ):
                project_guid = p.path.split('/')[-1].replace('.ht', '')
                self.dynamic_parquet_tasks.add(
                    self.clone(
                        MigrateProjectToClickHouseTask,
                        run_id=f'{self.run_id}_{sample_type.value}_{project_guid}',
                        sample_type=sample_type,
                        project_guid=project_guid,
                    ),
                )
        yield self.dynamic_parquet_tasks
