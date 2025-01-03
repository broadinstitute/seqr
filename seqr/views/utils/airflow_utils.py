from django.contrib.auth.models import User
import google.auth
from google.auth.transport.requests import AuthorizedSession
import json

from seqr.models import Project, Family
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.search.add_data_utils import prepare_data_loading_request, dag_dataset_type, reference_genome_version
from seqr.utils.logging_utils import SeqrLogger
from settings import AIRFLOW_WEBSERVER_URL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)

LOADING_PIPELINE_DAG_NAME = 'LOADING_PIPELINE'
DELETE_FAMILIES_DAG_NAME = 'DELETE_FAMILIES'
AIRFLOW_AUTH_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
SEQR_V3_PEDIGREE_GS_PATH = 'gs://seqr-loading-temp/v3.1'


class DagRunningException(Exception):
    pass


def trigger_airflow_data_loading(
    *args, user: User, individual_ids: list[int], success_message: str, success_slack_channel: str,
    error_message: str, is_internal: bool = False, **kwargs
) -> bool:
    updated_variables, gs_path = prepare_data_loading_request(
        *args, user, individual_ids=individual_ids, pedigree_dir=SEQR_V3_PEDIGREE_GS_PATH, **kwargs,
    )
    updated_variables['sample_source'] = 'Broad_Internal' if is_internal else 'AnVIL'
    upload_info = [f'Pedigree files have been uploaded to {gs_path}']
    return _trigger_airflow_dag(
        dag_name=LOADING_PIPELINE_DAG_NAME,
        user=user,
        variables=updated_variables,
        success_message=success_message,
        success_slack_channel=success_slack_channel,
        error_message=error_message,
        upload_info=upload_info
    )


def trigger_airflow_delete_families(
    dataset_type: str, genome_version: str, error_message: str, families: list[Family],
    projects: list[Project], success_message: str, success_slack_channel: str
):
    variables = {
        'projects_to_run': sorted([p.guid for p in projects]),
        'family_guids': sorted([f.guid for f in families]),
        'reference_genome': reference_genome_version(genome_version),
        'dataset_type': dag_dataset_type(dataset_type),
    }
    return _trigger_airflow_dag(
        dag_name=DELETE_FAMILIES_DAG_NAME,
        variables=variables,
        success_message=success_message,
        success_slack_channel=success_slack_channel,
        error_message=error_message,
        check_tasks=False,
    )


def _trigger_airflow_dag(
    dag_name: str, variables: dict, success_message: str, success_slack_channel: str,
    error_message: str, upload_info: list[str] = None, user: User = None, check_tasks = True
) -> bool:
    success = True
    try:
        _check_dag_running_state(dag_name)
        _update_variables(variables, dag_name)
        if check_tasks:
            _wait_for_dag_variable_update_via_tasks(variables['projects_to_run'], dag_name)
        else:
            _wait_for_dag_variable_update(variables, dag_name)
        _trigger_dag(dag_name)
    except Exception as e:
        logger_call = logger.warning if isinstance(e, DagRunningException) else logger.error
        logger_call(str(e), user)
        _send_slack_msg_on_failure_trigger(dag_name, e, variables, error_message)
        success = False

    if success or success_slack_channel != SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL:
        combined_message = [success_message]
        if upload_info:
            combined_message += upload_info
        _send_load_data_slack_msg(dag_name, combined_message, success_slack_channel, variables)
    return success


def _send_load_data_slack_msg(dag_name: str, messages: list[str], channel: str, dag: dict):
    message = '\n\n        '.join(messages)
    message_content = f"""{message}

        DAG {dag_name} is triggered with following:
        ```{json.dumps(dag, indent=4)}```
    """
    safe_post_to_slack(channel, message_content)


def _send_slack_msg_on_failure_trigger(dag_name: str, e, dag, error_message):
    message_content = f"""{error_message}: {e}

        DAG {dag_name} should be triggered with following: 
        ```{json.dumps(dag, indent=4)}```
        """
    safe_post_to_slack(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message_content)


def _check_dag_running_state(dag_name: str):
    endpoint = f'dags/{dag_name}/dagRuns'
    resp = _make_airflow_api_request(endpoint, method='GET')
    dag_runs = resp['dag_runs']
    if dag_runs and dag_runs[-1]['state'] not in {'success', 'failed'}:
        raise DagRunningException(f'{dag_name} DAG is running and cannot be triggered again.')


def _wait_for_dag_variable_update_via_tasks(projects: list[str], dag_name: str):
    dag_projects = _get_task_ids(dag_name)
    while all(p not in ''.join(dag_projects) for p in projects):
        dag_projects = _get_task_ids(dag_name)


def _wait_for_dag_variable_update(variables: dict, dag_name: str):
    existing_variables = _get_variables(dag_name)
    while any(existing_variables.get(k) != v for k, v in variables.items()):
        existing_variables = _get_variables(dag_name)


def _update_variables(val: dict, dag_name: str):
    endpoint = f'variables/{dag_name}'
    val_str = json.dumps(val)
    json_data = {
        "key": dag_name,
        "value": val_str
    }
    _make_airflow_api_request(endpoint, method='PATCH', json=json_data)


def _get_task_ids(dag_name: str):
    endpoint = f'dags/{dag_name}/tasks'
    airflow_response = _make_airflow_api_request(endpoint, method='GET')

    tasks = airflow_response['tasks']
    task_ids = [task_dict['task_id'] for task_dict in tasks]
    return task_ids

def _get_variables(dag_name: str):
    endpoint = f'dags/{dag_name}/variables'
    airflow_response = _make_airflow_api_request(endpoint, method='GET')
    return airflow_response['variables']


def _trigger_dag(dag_name: str):
    endpoint = f'dags/{dag_name}/dagRuns'
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
