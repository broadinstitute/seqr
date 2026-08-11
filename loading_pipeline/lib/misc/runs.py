import datetime
import os
from collections import defaultdict

import hailtop.fs as hfs

from loading_pipeline.lib.core.dataset_type import DatasetType
from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.misc.retry import retry
from loading_pipeline.lib.paths import (
    clickhouse_load_fail_file_path,
    clickhouse_load_success_file_path,
    loading_pipeline_queue_dir,
    pipeline_run_success_file_path,
)


def new_run_id():
    return datetime.datetime.now(datetime.UTC).strftime(
        '%Y%m%d-%H%M%S-%f',
    )


def get_oldest_queue_path() -> str | None:
    """
    Returns the path of the oldest loading pipeline request file in the queue directory.
    If the directory is empty, returns None.
    """
    queue_dir = loading_pipeline_queue_dir()
    queue_files = os.listdir(queue_dir)

    if len(queue_files) == 0:
        return None
    queue_files = [os.path.join(queue_dir, queue_file) for queue_file in queue_files]
    return min(queue_files, key=os.path.getctime)


def is_queue_full() -> bool:
    """
    Checks if the loading pipeline queue directory is full.
    Returns True if the number of files exceeds a predefined limit, otherwise False.
    """
    return len(os.listdir(loading_pipeline_queue_dir())) >= Env.LOADING_QUEUE_LIMIT


@retry()
def get_run_ids() -> tuple[defaultdict, defaultdict, defaultdict]:
    successful_pipeline_runs, successful_clickhouse_loads, failed_clickhouse_loads = (
        defaultdict(set),
        defaultdict(set),
        defaultdict(set),
    )
    for dataset_type in DatasetType:
        for reference_genome in dataset_type.reference_genomes:
            successful_pipeline_runs[(reference_genome, dataset_type)] = {
                p.path.split('/')[-2]
                for p in hfs.ls(
                    pipeline_run_success_file_path(
                        reference_genome,
                        dataset_type,
                        '*',
                    ),
                )
            }
            successful_clickhouse_loads[(reference_genome, dataset_type)] = {
                p.path.split('/')[-2]
                for p in hfs.ls(
                    clickhouse_load_success_file_path(
                        reference_genome,
                        dataset_type,
                        '*',
                    ),
                )
            }
            failed_clickhouse_loads[(reference_genome, dataset_type)] = {
                p.path.split('/')[-2]
                for p in hfs.ls(
                    clickhouse_load_fail_file_path(
                        reference_genome,
                        dataset_type,
                        '*',
                    ),
                )
            }
    return (
        successful_pipeline_runs,
        successful_clickhouse_loads,
        failed_clickhouse_loads,
    )
