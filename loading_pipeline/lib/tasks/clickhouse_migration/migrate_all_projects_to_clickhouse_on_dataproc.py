import luigi

from loading_pipeline.lib.tasks.clickhouse_migration.migrate_all_projects_to_clickhouse import (
    MigrateAllProjectsToClickHouseTask,
)
from loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc import (
    BaseRunJobOnDataprocTask,
)


class MigrateAllProjectsToClickHouseOnDataprocTask(BaseRunJobOnDataprocTask):
    run_id = luigi.Parameter()

    @property
    def task(self) -> luigi.Task:
        return MigrateAllProjectsToClickHouseTask
