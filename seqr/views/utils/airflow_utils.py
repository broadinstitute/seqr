from django.contrib.auth.models import User
import google.auth
from google.auth.transport.requests import AuthorizedSession
import json

from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.search.add_data_utils import prepare_data_loading_request
from seqr.utils.logging_utils import SeqrLogger
from settings import AIRFLOW_WEBSERVER_URL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)

DAG_NAME = 'LOADING_PIPELINE'
AIRFLOW_AUTH_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
SEQR_V3_PEDIGREE_GS_PATH = 'gs://seqr-loading-temp/v3.1'


class DagRunningException(Exception):
    pass


def trigger_airflow_data_loading(*args, user: User, success_message: str, success_slack_channel: str,
                                 error_message: str, is_internal: bool = False, **kwargs):

    success = True
    updated_variables, gs_path = prepare_data_loading_request(
        *args, user, pedigree_dir=SEQR_V3_PEDIGREE_GS_PATH, **kwargs,
    )
    updated_variables['sample_source'] = 'Broad_Internal' if is_internal else 'AnVIL'
    upload_info = [f'Pedigree files have been uploaded to {gs_path}']

    try:
        _check_dag_running_state()
        _update_variables(updated_variables)
        _wait_for_dag_variable_update(updated_variables['projects_to_run'])
        _trigger_dag()
    except Exception as e:
        logger_call = logger.warning if isinstance(e, DagRunningException) else logger.error
        logger_call(str(e), user)
        _send_slack_msg_on_failure_trigger(e, updated_variables, error_message)
        success = False

    if success or success_slack_channel != SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL:
        _send_load_data_slack_msg([success_message] + upload_info, success_slack_channel, updated_variables)
    return success


def _send_load_data_slack_msg(messages: list[str], channel: str, dag: dict):
    message = '\n\n        '.join(messages)
    message_content = f"""{message}

        DAG {DAG_NAME} is triggered with following:
        ```{json.dumps(dag, indent=4)}```
    """
    safe_post_to_slack(channel, message_content)


def _send_slack_msg_on_failure_trigger(e, dag, error_message):
    message_content = f"""{error_message}: {e}
        
        DAG {DAG_NAME} should be triggered with following: 
        ```{json.dumps(dag, indent=4)}```
        """
    safe_post_to_slack(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message_content)


def _check_dag_running_state():
    endpoint = f'dags/{DAG_NAME}/dagRuns'
    resp = _make_airflow_api_request(endpoint, method='GET')
    dag_runs = resp['dag_runs']
    if dag_runs and dag_runs[-1]['state'] == 'running':
        raise DagRunningException(f'{DAG_NAME} DAG is running and cannot be triggered again.')


def _wait_for_dag_variable_update(projects):
    dag_projects = _get_task_ids()
    while all(p not in ''.join(dag_projects) for p in projects):
        dag_projects = _get_task_ids()


def _update_variables(val):
    endpoint = f'variables/{DAG_NAME}'
    val_str = json.dumps(val)
    json_data = {
        "key": DAG_NAME,
        "value": val_str
        }
    _make_airflow_api_request(endpoint, method='PATCH', json=json_data)


def _get_task_ids():
    endpoint = f'dags/{DAG_NAME}/tasks'
    airflow_response = _make_airflow_api_request(endpoint, method='GET')

    tasks = airflow_response['tasks']
    task_ids = [task_dict['task_id'] for task_dict in tasks]
    return task_ids


def _trigger_dag():
    endpoint = f'dags/{DAG_NAME}/dagRuns'
    _make_airflow_api_request(endpoint, method='POST', json={})


def _make_airflow_api_request(endpoint, method='GET', timeout=90, **kwargs):
    credentials, _ = google.auth.default(scopes=[AIRFLOW_AUTH_SCOPE])
    authed_session = AuthorizedSession(credentials)
    resp = authed_session.request(
        method,
        f'{AIRFLOW_WEBSERVER_URL}/api/v1/{endpoint}',
        **kwargs
    )
    resp.raise_for_status()
    return resp.json()
