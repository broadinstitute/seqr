from collections import defaultdict, OrderedDict
from datetime import datetime
from django.db.models import F
import itertools
import json
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import re
import requests

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.models import Individual, Sample
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.file_utils import get_gs_file_list, does_file_exist
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
    dag_name = _construct_dag_name(sample_type, is_internal, dataset_type)
    updated_variables = _construct_dag_variables(
        projects, data_path, genome_version, dag_name, is_internal, user)
    dag_id = f'seqr_vcf_to_es_{dag_name}_v{AIRFLOW_DAG_VERSION}'

    upload_info = []
    if upload_files:
        upload_info = _upload_data_loading_files(upload_files, projects, genome_version, dag_name, is_internal, user)

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


def write_data_loading_pedigree(project, user):
    possible_dag_names = [
        _construct_dag_name(sample_type, is_internal=True, callset=callset) 
        for callset, sample_type in itertools.product(['Internal', 'External'], ['WGS', 'WES'])
    ]
    dag_name = next((dag_name for dag_name in possible_dag_names if does_file_exist(
        _get_dag_project_gs_path(project.guid, project.genome_version, dag_name, is_internal=True)
    )), None)
    if not dag_name:
        raise ValueError(f'No {SEQR_DATSETS_GS_PATH} project directory found for {project.guid}')
    _write_projects_pedigrees([project], project.genome_version, dag_name, user, is_internal=True)


def _write_projects_pedigrees(projects, genome_version, dag_name, user, is_internal):
    # TODO share behavior for _upload_data_loading_files
    annotations = OrderedDict({
        'Project_GUID': F('family__project__guid'), 'Family_GUID': F('family__guid'), 'Family_ID': F('family__family_id'),
        'Individual_ID': F('individual_id'),
        'Paternal_ID': F('father__individual_id'), 'Maternal_ID': F('mother__individual_id'), 'Sex': F('sex'),
    })
    data = Individual.objects.filter(family__project__in=projects).order_by('family_id', 'individual_id').values(
        **dict(annotations))
    data_by_project = defaultdict(list)
    for row in data:
        data_by_project[row['Project_GUID']].append(row)
    for project_guid, rows in data_by_project.items():
        gs_path = _get_dag_project_gs_path(project_guid, genome_version, dag_name, is_internal)
        write_multiple_files_to_gs(
            [(f'{project_guid}_pedigree', annotations.keys(), rows)], gs_path, user, file_format='tsv')


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


def _construct_dag_name(sample_type, is_internal, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, callset='Internal'):
    if is_internal:
        dag_dataset_type = '_GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
            else f'_{dataset_type}'
        return f'RDG_{sample_type}_Broad_{callset}{"" if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else dag_dataset_type}'
    return f'AnVIL_{sample_type}'


def _construct_dag_variables(projects, data_path, genome_version, dag_name, is_internal, user):
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
        path = _get_dag_gs_path(genome_version, dag_name)
        dag_variables['project_path'] = f'{path}/{projects[0]}/v{datetime.now().strftime("%Y%m%d")}'
    return dag_variables


def _upload_data_loading_files(upload_files, projects, genome_version, dag_name, is_internal, user):
    # TODO compute sample_ids from project models
    gs_path = _get_dag_project_gs_path(projects[0], genome_version, dag_name, is_internal)
    try:
        write_multiple_files_to_gs(upload_files, gs_path, user, file_format='txt')
    except Exception as e:
        logger.error(
            f'Uploading sample IDs to Google Storage failed. Errors: {e}', user,
            detail=[row['s'] for row in upload_files[0][2]],
        )
    return [f'The sample IDs to load have been uploaded to {gs_path}']


def _get_dag_project_gs_path(project, genome_version, dag_name, is_internal):
    dag_path = _get_dag_gs_path(genome_version, dag_name)
    return f'{dag_path}/base/projects/{project}' if is_internal else f'{dag_path}/{project}/base'


def _get_dag_gs_path(genome_version, dag_name):
    return f'{SEQR_DATSETS_GS_PATH}/{GENOME_VERSION_LOOKUP[genome_version]}/{dag_name}'


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
