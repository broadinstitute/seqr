#!/usr/bin/env python3
import json
import os
import re
import signal
import sys
import time

from loading_pipeline.api.model import (
    PipelineRunnerRequest,
)
from loading_pipeline.api.request_handlers import REQUEST_HANDLER_MAP
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.clickhouse import (
    drop_staging_db,
)
from loading_pipeline.lib.misc.runs import get_oldest_queue_path
from loading_pipeline.lib.misc.slack import (
    safe_post_to_slack_failure,
    safe_post_to_slack_success,
)
from loading_pipeline.lib.paths import (
    loading_pipeline_deadletter_queue_dir,
    loading_pipeline_deadletter_queue_path,
    loading_pipeline_queue_path,
)

logger = get_logger(__name__)


def signal_handler(*_):
    drop_staging_db()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def parse_run_id(latest_queue_path: str) -> str:
    m = re.search(
        r'request_(\d{8}-\d{6}-\d{6})\.json',
        os.path.basename(latest_queue_path),
    )
    if not m:
        msg = f'Invalid queue filename: {latest_queue_path}'
        raise ValueError(msg)
    return m.group(1)


def parse_latest_queue_path(
    latest_queue_path: str,
) -> PipelineRunnerRequest:
    with open(latest_queue_path) as f:
        raw_json = json.load(f)
    request_type_name = raw_json['request_type']
    request_cls = next(
        (cls for cls in REQUEST_HANDLER_MAP if cls.__name__ == request_type_name),
        None,
    )
    if not request_cls:
        msg = f'Unknown request_type: {request_type_name}'
        raise ValueError(msg)
    return request_cls.model_validate(raw_json)


def process_queue(local_scheduler=False):
    run_id, prr = None, None
    try:
        latest_queue_path = get_oldest_queue_path()
        if latest_queue_path is None:
            return
        run_id = parse_run_id(latest_queue_path)
        if not run_id:
            return
        prr = parse_latest_queue_path(latest_queue_path)
        REQUEST_HANDLER_MAP[type(prr)](prr, run_id, local_scheduler)
        os.remove(latest_queue_path)
        safe_post_to_slack_success(
            run_id,
            prr,
        )
    except Exception as e:
        logger.exception('Unhandled Exception')
        if run_id is None:
            return
        if hasattr(prr, 'attempt_id') and prr.incr_attempt():
            with open(loading_pipeline_queue_path(run_id), 'w') as f:
                f.write(prr.model_dump_json())
            return
        safe_post_to_slack_failure(
            run_id,
            prr,
            e,
        )
        os.makedirs(loading_pipeline_deadletter_queue_dir(), exist_ok=True)
        with open(loading_pipeline_deadletter_queue_path(run_id), 'w') as f:
            f.write(prr.model_dump_json())
        os.remove(latest_queue_path)


def main():
    while True:
        process_queue()
        logger.info('Looking for more work')
        time.sleep(1)


if __name__ == '__main__':
    main()
