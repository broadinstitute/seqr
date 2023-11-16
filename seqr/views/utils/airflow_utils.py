from datetime import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import re
import requests

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.models import Sample
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.file_utils import get_gs_file_list
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import SEQR_DATSETS_GS_PATH
from seqr.views.utils.export_utils import write_multiple_files_to_gs
from settings import AIRFLOW_API_AUDIENCE, AIRFLOW_WEBSERVER_URL, AIRFLOW_DAG_VERSION, \
    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)


class DagRunningException(Exception):
    pass


def trigger_data_loading(projects, sample_type, data_path, user, success_message, success_slack_channel, error_message,
                         dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, genome_version=GENOME_VERSION_GRCh38,
                         is_internal=False, upload_files=None):
    success = True
    dag_name = _construct_dag_name(sample_type, dataset_type, is_internal)
    updated_variables = _construct_dag_variables(
        projects, data_path, sample_type, genome_version, dag_name, is_internal, user)
    dag_id = f'seqr_vcf_to_es_{dag_name}_v{AIRFLOW_DAG_VERSION}'

    upload_info = []
    if upload_files:
        upload_info = _upload_data_loading_files(upload_files, projects, genome_version, sample_type, user)

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
        _send_load_data_slack_msg([success_message] + upload_info, success_slack_channel, dag_id, updated_variables)
    return success


def _send_load_data_slack_msg(messages, channel, dag_id, dag):
    message = '\n\n        '.join(messages)
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


def _construct_dag_name(sample_type, dataset_type, is_internal):
    if is_internal:
        dag_dataset_type = 'GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
            else dataset_type
        return f'RDG_{sample_type}_Broad_Internal_{dag_dataset_type}'
    return f'AnVIL_{sample_type}'


def _construct_dag_variables(projects, data_path, sample_type, genome_version, dag_name, is_internal, user):
    dag_variables = {
        "active_projects": projects,
        "projects_to_run": projects,
        "vcf_path": data_path,
    }
    if is_internal:
        version_path_prefix = f'{SEQR_DATSETS_GS_PATH}/{GENOME_VERSION_LOOKUP[genome_version]}/{dag_name}'
        version_paths = get_gs_file_list(version_path_prefix, user=user, allow_missing=True, check_subfolders=False)
        versions = [re.findall(f'{version_path_prefix}/v(\d\d)/', p) for p in version_paths]
        curr_version = max([int(v[0]) for v in versions if v] + [0])
        dag_variables['version_path'] = f'{version_path_prefix}/v{curr_version + 1:02d}'
    else:
        path = _get_anvil_loading_project_path(projects[0], genome_version, sample_type)
        dag_variables['project_path'] = f'{path}/v{datetime.now().strftime("%Y%m%d")}'
    return dag_variables


def _upload_data_loading_files(upload_files, projects, genome_version, sample_type, user):
    gs_path = f'{_get_anvil_loading_project_path(projects[0], genome_version, sample_type)}/base'
    try:
        write_multiple_files_to_gs(upload_files, gs_path, user, file_format='txt')
    except Exception as e:
        logger.error(
            f'Uploading sample IDs to Google Storage failed. Errors: {e}', user,
            detail=[row['s'] for row in upload_files[0][2]],
        )
    return [f'The sample IDs to load have been uploaded to {gs_path}']


def _get_anvil_loading_project_path(project, genome_version, sample_type):
    return f'{SEQR_DATSETS_GS_PATH}/{GENOME_VERSION_LOOKUP[genome_version]}/AnVIL_{sample_type}/{project}'


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
