import json
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.logging_utils import SeqrLogger
from settings import AIRFLOW_API_AUDIENCE, AIRFLOW_WEBSERVER_URL, AIRFLOW_DAG_VERSION, \
    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)


class DagRunningException(Exception):
    pass


def trigger_data_loading(dag_name, projects, data_path, additional_dag_variables, user,
                         success_message, success_slack_channel, error_message):
    success = True
    updated_variables = _construct_dag_variables(projects, data_path, additional_dag_variables)
    dag_id = f'seqr_vcf_to_es_{dag_name}_v{AIRFLOW_DAG_VERSION}'

    try:
        _check_dag_running_state(dag_id)
        _update_variables(dag_name, updated_variables)
        _wait_for_dag_variable_update(dag_id, projects)
        _trigger_dag(dag_id)
    except Exception as e:
        logger_call = logger.warning if isinstance(e, DagRunningException) else logger.error
        logger_call(str(e), user)
        _send_slack_msg_on_failure_trigger(e, dag_id, updated_variables, error_message)
        success = False

    if success or success_slack_channel != SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL:
        _send_load_data_slack_msg(success_message, success_slack_channel, dag_id, updated_variables)
    return success


def _send_load_data_slack_msg(message, channel, dag_id, dag):
    message_content = f"""{message}

        DAG {dag_id} is triggered with following:
        ```{json.dumps(dag, indent=4)}```
    """
    safe_post_to_slack(channel, message_content)


def _send_slack_msg_on_failure_trigger(e, dag_id, dag, error_message):
    message_content = f"""{error_message}: {e}
        
        DAG {dag_id} should be triggered with following: 
        ```{json.dumps(dag, indent=4)}```
        """
    safe_post_to_slack(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message_content)


def _check_dag_running_state(dag_id):
    endpoint = 'dags/{}/dagRuns'.format(dag_id)
    resp = _make_airflow_api_request(endpoint, method='GET')
    dag_runs = resp['dag_runs']
    if dag_runs and dag_runs[-1]['state'] == 'running':
        raise DagRunningException(f'{dag_id} is running and cannot be triggered again.')


def _construct_dag_variables(projects, data_path, additional_variables):
    dag_variables = {
        "active_projects": projects,
        "projects_to_run": projects,
        "vcf_path": data_path,
    }
    dag_variables.update(additional_variables)
    return dag_variables


def _wait_for_dag_variable_update(dag_id, projects):
    dag_projects = _get_task_ids(dag_id)
    while all(p not in ''.join(dag_projects) for p in projects):
        dag_projects = _get_task_ids(dag_id)


def _update_variables(key, val):
    endpoint = 'variables/{}'.format(key)
    val_str = json.dumps(val)
    json_data = {
        "key": key,
        "value": val_str
        }
    _make_airflow_api_request(endpoint, method='PATCH', json=json_data)


def _get_task_ids(dag_id):
    endpoint = 'dags/{}/tasks'.format(dag_id)
    airflow_response = _make_airflow_api_request(endpoint, method='GET')

    tasks = airflow_response['tasks']
    task_ids = [task_dict['task_id'] for task_dict in tasks]
    return task_ids


def _trigger_dag(dag_id):
    endpoint = 'dags/{}/dagRuns'.format(dag_id)
    _make_airflow_api_request(endpoint, method='POST', json={})


def _make_airflow_api_request(endpoint, method='GET', timeout=90, **kwargs):
    # Obtain an OpenID Connect (OIDC) token from metadata server or using service
    # account.
    google_open_id_connect_token = id_token.fetch_id_token(Request(), AIRFLOW_API_AUDIENCE)

    webserver_url = f'{AIRFLOW_WEBSERVER_URL}/api/v1/{endpoint}'
    resp = requests.request(
        method, webserver_url,
        headers={'Authorization': 'Bearer {}'.format(
            google_open_id_connect_token)}, **kwargs)

    resp.raise_for_status()
    return resp.json()
