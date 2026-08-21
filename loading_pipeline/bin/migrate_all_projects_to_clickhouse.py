#!/usr/bin/env python3
import uuid

import hailtop.fs as hfs
import luigi

from loading_pipeline.lib.core import (
    DatasetType,
    FeatureFlag,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.core.constants import MIGRATION_RUN_ID
from loading_pipeline.lib.paths import project_table_path
from loading_pipeline.lib.tasks import (
    MigrateAllProjectsToClickHouseOnDataprocTask,
    MigrateAllProjectsToClickHouseTask,
)
from loading_pipeline.lib.tasks.write_clickhouse_load_success_file import (
    WriteClickhouseLoadSuccessFileTask,
)

if __name__ == '__main__':
    task_cls = (
        MigrateAllProjectsToClickHouseOnDataprocTask
        if FeatureFlag.RUN_PIPELINE_ON_DATAPROC
        else MigrateAllProjectsToClickHouseTask
    )
    run_id_prefix = (
        MIGRATION_RUN_ID + '-' + str(uuid.uuid1().int)[:4]
    )  # Note: the randomness is a cache bust for the luigi local scheduler
    luigi.build(
        [
            task_cls(
                reference_genome,
                DatasetType.SNV_INDEL,
                run_id=run_id_prefix,
                attempt_id=0,
            )
            for reference_genome in ReferenceGenome
        ],
    )
    clickhouse_load_tasks = []
    for sample_type in SampleType:
        for reference_genome in ReferenceGenome:
            for p in hfs.ls(
                project_table_path(
                    reference_genome,
                    DatasetType.SNV_INDEL,
                    sample_type,
                    '*',
                ),
            ):
                project_guid = p.path.split('/')[-1].replace('.ht', '')
                clickhouse_load_tasks.append(
                    WriteClickhouseLoadSuccessFileTask(
                        reference_genome=reference_genome,
                        dataset_type=DatasetType.SNV_INDEL,
                        run_id=f'{run_id_prefix}_{sample_type.value}_{project_guid}',
                        callset_path='',
                        sample_type=sample_type,
                        attempt_id=0,
                    ),
                )
    luigi.build(clickhouse_load_tasks)
