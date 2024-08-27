from collections import defaultdict, OrderedDict
from django.contrib.auth.models import User
from django.db.models import F
import google.auth
from google.auth.transport.requests import AuthorizedSession
import json

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.models import Individual, Sample, Project
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.export_utils import write_multiple_files_to_gs
from settings import AIRFLOW_WEBSERVER_URL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)

DAG_NAME = 'LOADING_PIPELINE'
AIRFLOW_AUTH_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
SEQR_V2_DATASETS_GS_PATH = 'gs://seqr-datasets/v02'
SEQR_V3_PEDIGREE_GS_PATH = 'gs://seqr-loading-temp/v3.1'


class DagRunningException(Exception):
    pass


def trigger_data_loading(projects: list[Project], sample_type: str, dataset_type: str, data_path: str, user: User,
                         success_message: str, success_slack_channel: str, error_message: str,
                         genome_version: str = GENOME_VERSION_GRCh38, is_internal: bool = False,
                         individual_ids: list[str] = None):

    success = True
    project_guids = sorted([p.guid for p in projects])
    updated_variables = {
        'projects_to_run': project_guids,
        'callset_path': data_path,
        'sample_source': 'Broad_Internal' if is_internal else 'AnVIL',
        'sample_type': sample_type,
        'dataset_type': _dag_dataset_type(sample_type, dataset_type),
        'reference_genome': GENOME_VERSION_LOOKUP[genome_version],
    }

    upload_info = _upload_data_loading_files(projects, user, genome_version, sample_type, dataset_type, individual_ids)

    try:
        _check_dag_running_state()
        _update_variables(updated_variables)
        _wait_for_dag_variable_update(project_guids)
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


def _dag_dataset_type(sample_type: str, dataset_type: str):
    return 'GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
        else dataset_type


def _upload_data_loading_files(projects: list[Project], user: User, genome_version: str, sample_type: str, dataset_type: str,
                               individual_ids: list[str]):
    file_annotations = OrderedDict({
        'Project_GUID': F('family__project__guid'), 'Family_GUID': F('family__guid'),
        'Family_ID': F('family__family_id'),
        'Individual_ID': F('individual_id'),
        'Paternal_ID': F('father__individual_id'), 'Maternal_ID': F('mother__individual_id'), 'Sex': F('sex'),
    })
    annotations = {'project': F('family__project__guid'), **file_annotations}
    individual_filter = {'id__in': individual_ids} if individual_ids else {'family__project__in': projects}
    data = Individual.objects.filter(**individual_filter).order_by('family_id', 'individual_id').values(
        **dict(annotations))

    data_by_project = defaultdict(list)
    for row in data:
        data_by_project[row.pop('project')].append(row)

    info = []
    header = list(file_annotations.keys())
    files = [(f'{project_guid}_pedigree', header, rows) for project_guid, rows in data_by_project.items()]
    gs_path = _get_gs_pedigree_path(genome_version, sample_type, dataset_type)
    try:
        write_multiple_files_to_gs(files, gs_path, user, file_format='tsv')
    except Exception as e:
        logger.error(f'Uploading Pedigrees to Google Storage failed. Errors: {e}', user, detail={
            project: rows for project, _, rows in files
        })
    info.append(f'Pedigree files have been uploaded to {gs_path}')

    return info


def _get_gs_pedigree_path(genome_version: str, sample_type: str, dataset_type: str):
    return f'{SEQR_V3_PEDIGREE_GS_PATH}/{GENOME_VERSION_LOOKUP[genome_version]}/{dataset_type}/pedigrees/{sample_type}/'


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
