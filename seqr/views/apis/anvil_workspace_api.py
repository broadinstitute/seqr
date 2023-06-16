"""APIs for management of projects related to AnVIL workspaces."""
import json
import time
import tempfile
import os
import re
from datetime import datetime
from functools import wraps
from collections import defaultdict
import requests

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Project, CAN_EDIT, Sample
from seqr.views.react_app import render_app_html
from seqr.views.utils.airtable_utils import AirtableSession
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS, SEQR_DATSETS_GS_PATH
from seqr.utils.search.utils import get_search_samples
from seqr.views.utils.json_to_orm_utils import create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.views.utils.terra_api_utils import add_service_account, has_service_account_access, TerraAPIException, \
    TerraRefreshTokenFailedException
from seqr.views.utils.pedigree_info_utils import parse_basic_pedigree_table, JsonConstants
from seqr.views.utils.individual_utils import add_or_update_individuals_and_families
from seqr.utils.communication_utils import safe_post_to_slack, send_html_email
from seqr.utils.file_utils import does_file_exist, mv_file_to_gs, get_gs_file_list
from seqr.utils.vcf_utils import validate_vcf_and_get_samples
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.permissions_utils import is_anvil_authenticated, check_workspace_perm, login_and_policies_required
from settings import BASE_URL, GOOGLE_LOGIN_REQUIRED_URL, POLICY_REQUIRED_URL, API_POLICY_REQUIRED_URL,\
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, AIRFLOW_API_AUDIENCE, AIRFLOW_WEBSERVER_URL, ANVIL_LOADING_DELAY_EMAIL_START_DATE, \
    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)

anvil_auth_required = user_passes_test(is_anvil_authenticated, login_url=GOOGLE_LOGIN_REQUIRED_URL)

DAG_VERSION = '0.0.1'


def save_temp_data(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as fp:
        fp.write(data)
        return fp.name


def anvil_auth_and_policies_required(wrapped_func=None, policy_url=API_POLICY_REQUIRED_URL):
    def decorator(view_func):
        return login_and_policies_required(anvil_auth_required(view_func), login_url=GOOGLE_LOGIN_REQUIRED_URL, policy_url=policy_url)
    if wrapped_func:
        return decorator(wrapped_func)
    return decorator


def anvil_workspace_access_required(wrapped_func=None, meta_fields=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, namespace, name, *args, **kwargs):
            # Validate that the current user has logged in through google and has sufficient permissions
            workspace_meta = check_workspace_perm(request.user, CAN_EDIT, namespace, name, can_share=True, meta_fields=meta_fields)
            if meta_fields:
                return view_func(request, namespace, name, workspace_meta, *args, **kwargs)
            return view_func(request, namespace, name, *args, **kwargs)
        return anvil_auth_and_policies_required(_wrapped_view)
    if wrapped_func:
        return decorator(wrapped_func)
    return decorator


@anvil_auth_and_policies_required(policy_url=POLICY_REQUIRED_URL)
def anvil_workspace_page(request, namespace, name):
    """
    This view will be requested from AnVIL, it validates the workspace and project before loading data.

    :param request: Django request object.
    :param namespace: The namespace (or the billing account) of the workspace.
    :param name: The name of the workspace. It also be used as the project name.
    :return Redirect to a page depending on if the workspace permissions or project exists.

    """
    project = Project.objects.filter(workspace_namespace=namespace, workspace_name=name)
    if project:
        return redirect('/project/{}/project_page'.format(project.first().guid))

    try:
        workspace_meta = check_workspace_perm(
            request.user, CAN_EDIT, namespace, name, can_share=True, meta_fields=['workspace.authorizationDomain'])
        if workspace_meta['workspace']['authorizationDomain']:
            logger.warning(
                f'Unable to load data from anvil workspace with authorization domains "{namespace}/{name}"', request.user
            )
            raise PermissionDenied
    except PermissionDenied:
        return render_app_html(request, status=403)
    except TerraRefreshTokenFailedException:
        return redirect_to_login(request.get_full_path(), GOOGLE_LOGIN_REQUIRED_URL)

    return redirect('/create_project_from_workspace/{}/{}'.format(namespace, name))


@anvil_workspace_access_required
def grant_workspace_access(request, namespace, name):
    request_json = json.loads(request.body)
    if not request_json.get('agreeSeqrAccess'):
        error = 'Must agree to grant seqr access to the data in the associated workspace.'
        return create_json_response({'error': error}, status=400, reason=error)

    # Add the seqr service account to the corresponding AnVIL workspace
    added_account_to_workspace = add_service_account(request.user, namespace, name)
    if added_account_to_workspace:
        logger.info(f'Added service account for {namespace}/{name}, waiting for access to grant', request.user)
        _wait_for_service_account_access(request.user, namespace, name)

    return create_json_response({'success': True})


@anvil_workspace_access_required(meta_fields=['workspace.bucketName'])
def get_anvil_vcf_list(request, namespace, name, workspace_meta):
    bucket_name = workspace_meta['workspace']['bucketName']
    bucket_path = 'gs://{bucket}'.format(bucket=bucket_name.rstrip('/'))
    data_path_list = [path.replace(bucket_path, '') for path in get_gs_file_list(bucket_path, request.user)
                      if path.endswith(VCF_FILE_EXTENSIONS)]
    data_path_list = _merge_sharded_vcf(data_path_list)

    return create_json_response({'dataPathList': data_path_list})


@anvil_workspace_access_required(meta_fields=['workspace.bucketName'])
def validate_anvil_vcf(request, namespace, name, workspace_meta):
    path = json.loads(request.body).get('dataPath')
    if not path:
        error = 'dataPath is required'
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate the data path
    bucket_name = workspace_meta['workspace']['bucketName']
    data_path = 'gs://{bucket}/{path}'.format(bucket=bucket_name.rstrip('/'), path=path.lstrip('/'))
    if not data_path.endswith(VCF_FILE_EXTENSIONS):
        error = 'Invalid VCF file format - file path must end with {}'.format(' or '.join(VCF_FILE_EXTENSIONS))
        return create_json_response({'error': error}, status=400, reason=error)

    file_to_check = None
    if '*' in data_path:
        files = get_gs_file_list(data_path, request.user, check_subfolders=False, allow_missing=True)
        if files:
            file_to_check = files[0]
    elif does_file_exist(data_path, user=request.user):
        file_to_check = data_path

    if not file_to_check:
        error = 'Data file or path {} is not found.'.format(path)
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate the VCF to see if it contains all the required samples
    samples = validate_vcf_and_get_samples(file_to_check)

    return create_json_response({'vcfSamples': sorted(samples), 'fullDataPath': data_path})


@anvil_workspace_access_required
def create_project_from_workspace(request, namespace, name):
    """
    Create a project when a cooperator requests to load data from an AnVIL workspace.

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return the projectsByGuid with the new project json

    """
    projects = Project.objects.filter(workspace_namespace=namespace, workspace_name=name)
    if projects:
        error = 'Project "{}" for workspace "{}/{}" exists.'.format(projects.first().name, namespace, name)
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate all the user inputs from the post body
    request_json = json.loads(request.body)

    missing_fields = [field for field in ['genomeVersion', 'uploadedFileId', 'fullDataPath', 'vcfSamples', 'sampleType'] if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    pedigree_records = _parse_uploaded_pedigree(request_json)

    # Create a new Project in seqr
    project_args = {
        'name': name,
        'genome_version': request_json['genomeVersion'],
        'description': request_json.get('description', ''),
        'workspace_namespace': namespace,
        'workspace_name': name,
        'mme_primary_data_owner': request.user.get_full_name(),
        'mme_contact_url': 'mailto:{}'.format(request.user.email),
    }

    project = create_model_from_json(Project, project_args, user=request.user)

    _trigger_add_workspace_data(project, pedigree_records, request.user, request_json['fullDataPath'], request_json['sampleType'])

    return create_json_response({'projectGuid': project.guid})


@anvil_auth_and_policies_required
def add_workspace_data(request, project_guid):
    """
    Add data from an AnVIL workspace.

    :param request: Django request object
    :param project_guid: Django request object
    :return a data json with fields of individualGuid, familyGuid and optional familyNotesByGuid if no exceptions

    """
    project = Project.objects.get(guid=project_guid)
    check_workspace_perm(request.user, CAN_EDIT, project.workspace_namespace, project.workspace_name, can_share=True)

    request_json = json.loads(request.body)

    missing_fields = [field for field in ['uploadedFileId', 'fullDataPath', 'vcfSamples'] if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    pedigree_records = _parse_uploaded_pedigree(request_json)

    previous_samples = get_search_samples([project]).filter(
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS).prefetch_related('individual')
    if not previous_samples:
        return create_json_response({
            'error': 'New data cannot be added to this project until the previously requested data is loaded',
        }, status=400)

    previous_loaded_individuals = {s.individual.individual_id for s in previous_samples}
    missing_loaded_samples = [individual_id for individual_id in previous_loaded_individuals if
                              individual_id not in request_json['vcfSamples']]
    if missing_loaded_samples:
        return create_json_response({
            'error': 'In order to add new data to this project, new samples must be joint called in a single VCF with all previously loaded samples.'
                     ' The following samples were previously loaded in this project but are missing from the VCF: {}'.format(
                ', '.join(sorted(missing_loaded_samples)))}, status=400)

    pedigree_json = _trigger_add_workspace_data(
        project, pedigree_records, request.user, request_json['fullDataPath'], previous_samples.first().sample_type,
        previous_loaded_ids=previous_loaded_individuals, get_pedigree_json=True)

    return create_json_response(pedigree_json)


def _parse_uploaded_pedigree(request_json):
    # Parse families/individuals in the uploaded pedigree file
    json_records = load_uploaded_file(request_json['uploadedFileId'])
    pedigree_records, _ = parse_basic_pedigree_table(
        json_records, 'uploaded pedigree file', required_columns=[
            JsonConstants.SEX_COLUMN, JsonConstants.AFFECTED_COLUMN,
        ])

    missing_samples = [record['individualId'] for record in pedigree_records
                       if record['individualId'] not in request_json['vcfSamples']]

    if missing_samples:
        error = 'The following samples are included in the pedigree file but are missing from the VCF: {}'.format(
                ', '.join(missing_samples))
        raise ErrorsWarningsException([error], [])

    return pedigree_records


def _trigger_add_workspace_data(project, pedigree_records, user, data_path, sample_type, previous_loaded_ids=None, get_pedigree_json=False):
    # add families and individuals according to the uploaded individual records
    pedigree_json, sample_ids = add_or_update_individuals_and_families(
        project, individual_records=pedigree_records, user=user, get_update_json=get_pedigree_json, get_updated_individual_ids=True,
    )
    num_updated_individuals = len(sample_ids)

    # Upload sample IDs to a file on Google Storage
    ids_path = '{}base/{guid}_ids.txt'.format(_get_loading_project_path(project, sample_type), guid=project.guid)
    sample_ids.update(previous_loaded_ids or [])
    try:
        temp_path = save_temp_data('\n'.join(['s'] + sorted(sample_ids)))
        mv_file_to_gs(temp_path, ids_path, user=user)
    except Exception as ee:
        logger.error('Uploading sample IDs to Google Storage failed. Errors: {}'.format(str(ee)), user,
                     detail=sorted(sample_ids))

    # use airflow api to trigger AnVIL dags
    trigger_success = _trigger_data_loading(project, data_path, sample_type, user)
    # Send a slack message to the slack channel
    _send_load_data_slack_msg(project, ids_path, data_path, num_updated_individuals, sample_type, user)
    AirtableSession(user, base=AirtableSession.ANVIL_BASE).safe_create_record(
        'AnVIL Seqr Loading Requests Tracking', {
            'Requester Name': user.get_full_name(),
            'Requester Email': user.email,
            'AnVIL Project URL': _get_seqr_project_url(project),
            'Initial Request Date': datetime.now().strftime('%Y-%m-%d'),
            'Number of Samples': len(sample_ids),
            'Status': 'Loading' if trigger_success else 'Loading Requested'
        })

    loading_warning_date = ANVIL_LOADING_DELAY_EMAIL_START_DATE and datetime.strptime(ANVIL_LOADING_DELAY_EMAIL_START_DATE, '%Y-%m-%d')
    if loading_warning_date and loading_warning_date <= datetime.now():
        try:
            email_body = f"""Hi {user.get_full_name() or user.email},
            We have received your request to load data to seqr from AnVIL. Currently, the Broad Institute is holding an 
            internal retreat or closed for the winter break so we are unable to load data until mid-January 
            {loading_warning_date.year + 1}. We appreciate your understanding and support of our research team taking 
            some well-deserved time off and hope you also have a nice break.
            - The seqr team
            """
            send_html_email(email_body, subject='Delay in loading AnVIL in seqr', to=[user.email])
        except Exception as e:
            logger.error('AnVIL loading delay email error: {}'.format(e), user)

    return pedigree_json

def _wait_for_service_account_access(user, namespace, name):
    for _ in range(2):
        time.sleep(3)
        if has_service_account_access(user, namespace, name):
            return True
    raise TerraAPIException('Failed to grant seqr service account access to the workspace', 400)


def _get_loading_project_path(project, sample_type):
    return f'{SEQR_DATSETS_GS_PATH}/{project.get_genome_version_display()}/AnVIL_{sample_type}/{project.guid}/'


def _get_seqr_project_url(project):
    return f'{BASE_URL}project/{project.guid}/project_page'

def _send_load_data_slack_msg(project, ids_path, data_path, sample_count, sample_type, user):
    pipeline_dag = _construct_dag_variables(project, data_path, sample_type)
    message_content = """
        *{user}* requested to load {sample_count} {sample_type} samples ({genome_version}) from AnVIL workspace *{namespace}/{name}* at 
        {path} to seqr project <{project_url}|*{project_name}*> (guid: {guid})  
  
        The sample IDs to load have been uploaded to {ids_path}.  
  
        DAG {dag_name} is triggered with following:
        ```{dag}```
        """.format(
        user=user.email,
        path=data_path,
        ids_path=ids_path,
        namespace=project.workspace_namespace,
        name=project.workspace_name,
        project_url=_get_seqr_project_url(project),
        guid=project.guid,
        project_name=project.name,
        sample_count=sample_count,
        sample_type=sample_type,
        genome_version=GENOME_VERSION_LOOKUP.get(project.genome_version),
        dag_name = "seqr_vcf_to_es_AnVIL_{anvil_type}_v{version}".format(anvil_type=sample_type, version=DAG_VERSION),
        dag=json.dumps(pipeline_dag, indent=4),
    )

    safe_post_to_slack(SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, message_content)

def _send_slack_msg_on_failure_trigger(e, project, data_path, sample_type):
    pipeline_dag = _construct_dag_variables(project, data_path, sample_type)
    message_content = """
        ERROR triggering AnVIL loading for project {project_guid}: {e} 
        
        DAG {dag_name} should be triggered with following: 
        ```{dag}```
        """.format(
            project_guid = project.guid,
            e = e,
            dag_name = "seqr_vcf_to_es_AnVIL_{anvil_type}_v{version}".format(anvil_type=sample_type, version=DAG_VERSION),
            dag = json.dumps(pipeline_dag, indent=4)
        )
    safe_post_to_slack(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message_content)

def _trigger_data_loading(project, data_path, sample_type, user):
    try:
        genome_test_type = 'AnVIL_{sample_type}'.format(sample_type=sample_type)
        dag_id = "seqr_vcf_to_es_{anvil_type}_v{version}".format(anvil_type=genome_test_type, version=DAG_VERSION)

        _check_dag_running_state(dag_id)
        updated_anvil_variables = _construct_dag_variables(project, data_path, sample_type)
        _update_variables(genome_test_type, updated_anvil_variables)
        _wait_for_dag_variable_update(dag_id, project)

        _trigger_dag(dag_id)
        return True
    except Exception as e:
        logger_call = logger.warning if isinstance(e, DagRunningException) else logger.error
        logger_call(str(e), user)
        _send_slack_msg_on_failure_trigger(e, project, data_path, sample_type)
        return False

class DagRunningException(Exception):
    pass

def _check_dag_running_state(dag_id):
    endpoint = 'dags/{}/dagRuns'.format(dag_id)
    resp = _make_airflow_api_request(endpoint, method='GET')
    lastest_dag_runs = resp['dag_runs'][-1]
    if lastest_dag_runs['state'] == 'running':
        raise DagRunningException(f'{dag_id} is running and cannot be triggered again.')


def _construct_dag_variables(project, data_path, sample_type):
    dag_variables = {
        "active_projects": [project.guid],
        "vcf_path": data_path,
        "project_path": '{}v{}'.format(_get_loading_project_path(project, sample_type), datetime.now().strftime("%Y%m%d")),
        "projects_to_run": [project.guid],
    }
    return dag_variables


def _wait_for_dag_variable_update(dag_id, project):
    updated_project = project.guid
    dag_projects = _get_task_ids(dag_id)
    while updated_project not in ''.join(dag_projects):
        dag_projects = _get_task_ids(dag_id)

def _update_variables(key, val):
    endpoint = 'variables/{}'.format(key)
    val_str = json.dumps(val)
    json_data= {
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


def _merge_sharded_vcf(vcf_files):
    files_by_path = defaultdict(list)

    for vcf_file in vcf_files:
        subfolder_path, file = vcf_file.rsplit('/', 1)
        files_by_path[subfolder_path].append(file)

    # discover the sharded VCF files in each folder, replace the sharded VCF files with a single path with '*'
    for subfolder_path, files in files_by_path.items():
        if len(files) < 2:
            continue
        prefix = os.path.commonprefix(files)
        suffix = re.fullmatch(r'{}\d*(?P<suffix>\D.*)'.format(prefix), files[0]).groupdict()['suffix']
        if all([re.fullmatch(r'{}\d+{}'.format(prefix, suffix), file) for file in files]):
            files_by_path[subfolder_path] = [f'{prefix}*{suffix}']

    return [f'{path}/{file}' for path, files in files_by_path.items() for file in files]
