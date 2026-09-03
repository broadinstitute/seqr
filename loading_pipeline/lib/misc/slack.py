import json

from slacker import Slacker

from loading_pipeline.api.model import PipelineRunnerRequest
from loading_pipeline.lib.core import Env, FeatureFlag
from loading_pipeline.lib.logger import get_logger

DATAPROC_URL = 'https://console.cloud.google.com/dataproc/jobs?project={gcloud_project}'
SLACK_FAILURE_MESSAGE_PREFIX = ':failed: Pipeline Runner Request Failed :failed:'
SLACK_SUCCESS_MESSAGE_PREFIX = (
    ':white_check_mark: Pipeline Runner Request Success! :white_check_mark:'
)


logger = get_logger(__name__)


def _safe_post_to_slack(message) -> None:
    try:
        if not Env.SLACK_TOKEN:
            logger.info(message)
            return
        slack = Slacker(Env.SLACK_TOKEN)
        slack.chat.post_message(
            Env.SLACK_NOTIFICATION_CHANNEL,
            message,
            as_user=False,
            icon_emoji=':beaker:',
            username='Beaker (engineering-minion)',
        )
    except Exception:
        logger.exception(
            f'Slack error:  Original message in channel ({Env.SLACK_NOTIFICATION_CHANNEL}) - {message}',
        )


def safe_post_to_slack_failure(
    run_id: str,
    prr: PipelineRunnerRequest,
    e: type[Exception],
) -> None:
    message = [
        SLACK_FAILURE_MESSAGE_PREFIX,
        f'Run ID: {run_id}',
        f'```{json.dumps(prr.model_dump(), indent=4, sort_keys=True)}```',
        f'Reason: {e!s}',
    ]
    if FeatureFlag.RUN_PIPELINE_ON_DATAPROC:
        message = [
            *message,
            f'<{DATAPROC_URL.format(gcloud_project=Env.GCLOUD_PROJECT)}|Dataproc Jobs Page>',
        ]
    _safe_post_to_slack('\n'.join(message))


def safe_post_to_slack_success(run_id: str, prr: PipelineRunnerRequest) -> None:
    message = '\n'.join(
        [
            SLACK_SUCCESS_MESSAGE_PREFIX,
            f'Run ID: {run_id}',
            f'```{json.dumps(prr.model_dump(), indent=4, sort_keys=True)}```',
        ],
    )
    _safe_post_to_slack(message)
