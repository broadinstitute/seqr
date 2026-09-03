import datetime
import os

from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.paths import (
    loading_pipeline_queue_dir,
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
