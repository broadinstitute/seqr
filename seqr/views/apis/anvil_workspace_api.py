"""APIs for management of projects related to AnVIL workspaces."""
import json
import time
from datetime import datetime
from functools import wraps

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Project, Family, CAN_EDIT, Sample, IgvSample
from seqr.views.react_app import render_app_html
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.json_to_orm_utils import create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.views.utils.terra_api_utils import add_service_account, has_service_account_access, TerraAPIException, \
    TerraRefreshTokenFailedException
from seqr.views.utils.pedigree_info_utils import parse_basic_pedigree_table, JsonConstants
from seqr.views.utils.individual_utils import add_or_update_individuals_and_families
from seqr.utils.file_utils import list_files
from seqr.utils.search.add_data_utils import get_missing_family_samples, get_loaded_individual_ids, trigger_data_loading
from seqr.utils.vcf_utils import validate_vcf_and_get_samples, get_vcf_list
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.permissions_utils import is_anvil_authenticated, check_workspace_perm, login_and_policies_required
from settings import BASE_URL, GOOGLE_LOGIN_REQUIRED_URL, POLICY_REQUIRED_URL, API_POLICY_REQUIRED_URL,\
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL
logger = SeqrLogger(__name__)

anvil_auth_required = user_passes_test(is_anvil_authenticated, login_url=GOOGLE_LOGIN_REQUIRED_URL)


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


def _get_workspace_bucket(namespace, name, workspace_meta):
    bucket_name = workspace_meta['workspace']['bucketName']
    return 'gs://{bucket}'.format(bucket=bucket_name.rstrip('/'))


@anvil_workspace_access_required(meta_fields=['workspace.bucketName'])
def get_anvil_vcf_list(request, *args):
    bucket_path = _get_workspace_bucket(*args)
    data_path_list = get_vcf_list(bucket_path, request.user)

    return create_json_response({'dataPathList': data_path_list})


@anvil_workspace_access_required(meta_fields=['workspace.bucketName'])
def get_anvil_igv_options(request, *args):
    bucket_path = _get_workspace_bucket(*args)
    file_list = list_files(bucket_path, request.user, check_subfolders=True, allow_missing=False)
    igv_options = [
        {'name': path.replace(bucket_path, ''), 'value': path} for path in file_list
        if path.endswith(IgvSample.SAMPLE_TYPE_FILE_EXTENSIONS[IgvSample.SAMPLE_TYPE_ALIGNMENT])
    ]

    return create_json_response({'igv_options': igv_options})


@anvil_workspace_access_required(meta_fields=['workspace.bucketName'])
def validate_anvil_vcf(request, namespace, name, workspace_meta):
    body = json.loads(request.body)
    missing_fields = [field for field in ['genomeVersion', 'dataPath'] if not body.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate no pending loading projects
    pending_project = Project.objects.filter(
        created_by=request.user, genome_version=body['genomeVersion'],
        family__analysis_status=Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ).exclude(workspace_namespace=namespace, workspace_name=name).first()
    if pending_project:
        raise ErrorsWarningsException([
            f'Project "{pending_project.name}" is awaiting loading. Please wait for loading to complete and/or delete any families that will not be receiving data before requesting additional data loading'
        ])

    # Validate the data path
    path = body['dataPath']
    bucket_name = workspace_meta['workspace']['bucketName']
    data_path = 'gs://{bucket}/{path}'.format(bucket=bucket_name.rstrip('/'), path=path.lstrip('/'))

    # Validate the VCF to see if it contains all the required samples
    samples = validate_vcf_and_get_samples(data_path, request.user, body['genomeVersion'], path_name=path)

    return create_json_response({'vcfSamples': samples, 'fullDataPath': data_path})


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

    pedigree_records = _parse_uploaded_pedigree(request_json)[0]

    # Create a new Project in seqr
    project_args = {
        'name': name,
        'genome_version': request_json['genomeVersion'],
        'description': request_json.get('description', ''),
        'workspace_namespace': namespace,
        'workspace_name': name,
        'mme_primary_data_owner': request.user.get_full_name(),
        'mme_contact_url': 'mailto:{}'.format(request.user.email),
        'vlm_contact_email': request.user.email,
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

    pedigree_records, loaded_individual_ids, sample_type = _parse_uploaded_pedigree(request_json, project=project, search_dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)

    loading_families = {record[JsonConstants.FAMILY_ID_COLUMN] for record in pedigree_records}
    pending_families = Family.objects.filter(
        project=project, analysis_status=Family.ANALYSIS_STATUS_WAITING_FOR_DATA,
    ).exclude(family_id__in=loading_families).order_by('family_id').values_list('family_id', flat=True)
    if pending_families:
        raise ErrorsWarningsException([
            f'The following families in this project are awaiting loading from a previous loading request: {", ".join(pending_families)}. Please wait for loading to complete and/or delete any families that will not be receiving data before requesting additional data loading'
        ])

    pedigree_json = _trigger_add_workspace_data(
        project, pedigree_records, request.user, request_json['fullDataPath'], sample_type,
        previous_loaded_ids=loaded_individual_ids, get_pedigree_json=True)

    return create_json_response(pedigree_json)


def _parse_uploaded_pedigree(request_json, project=None, search_dataset_type=None):
    loaded_sample_types = [] if search_dataset_type else None
    loaded_individual_ids = []
    def validate_expected_samples(*args):
        return _validate_expected_samples(request_json['vcfSamples'], loaded_sample_types, loaded_individual_ids, *args)

    json_records = load_uploaded_file(request_json['uploadedFileId'])
    pedigree_records = parse_basic_pedigree_table(
        project, json_records, 'uploaded pedigree file', update_features=True, required_columns=[
            JsonConstants.SEX_COLUMN, JsonConstants.AFFECTED_COLUMN,
        ], search_dataset_type=search_dataset_type, validate_expected_samples=validate_expected_samples)

    return pedigree_records, loaded_individual_ids, loaded_sample_types[0] if loaded_sample_types else None


def _validate_expected_samples(vcf_samples, loaded_sample_types, loaded_individual_ids, record_family_ids, previous_loaded_individuals, sample_type):
    errors = []

    if loaded_sample_types is not None:
        if sample_type:
            loaded_sample_types.append(sample_type)
        else:
            errors.append('New data cannot be added to this project until the previously requested data is loaded')

    missing_vcf_samples = set(record_family_ids.keys()) - set(vcf_samples)
    if missing_vcf_samples:
        errors.append(
            f'The following samples are included in the pedigree file but are missing from the VCF: {", ".join(sorted(missing_vcf_samples))}',
        )

    missing_samples_by_family = get_missing_family_samples(vcf_samples, record_family_ids, previous_loaded_individuals)
    if missing_samples_by_family:
        missing_family_sample_messages = [
            f'Family {family_id}: {", ".join(sorted(individual_ids))}'
            for family_id, individual_ids in missing_samples_by_family.items()
        ]
        errors.append('\n'.join([
            'In order to load data for families with previously loaded data, new family samples must be joint called in a single VCF with all previously loaded samples. The following samples were previously loaded in this project but are missing from the VCF:',
        ] + sorted(missing_family_sample_messages)))

    loaded_individual_ids += get_loaded_individual_ids(record_family_ids, previous_loaded_individuals)

    return errors


def _trigger_add_workspace_data(project, pedigree_records, user, data_path, sample_type, previous_loaded_ids=None, get_pedigree_json=False):
    # add families and individuals according to the uploaded individual records
    pedigree_json, individual_ids = add_or_update_individuals_and_families(
        project, individual_records=pedigree_records, user=user, get_update_json=get_pedigree_json, get_updated_individual_db_ids=True,
        allow_features_update=True, skip_gt_stats_rebuild=True,
    )
    num_updated_individuals = len(individual_ids)
    individual_ids.update(previous_loaded_ids or [])

    # use airflow api to trigger AnVIL dags
    reload_summary = f' and {len(previous_loaded_ids)} re-loaded' if previous_loaded_ids else ''
    success_message = (
        f"*{user.email}* requested to load {num_updated_individuals} new{reload_summary} {sample_type} samples "
        f"({GENOME_VERSION_LOOKUP.get(project.genome_version)}) from AnVIL workspace *{project.workspace_namespace}/{project.workspace_name}* at "
        f"{data_path} to seqr project <{_get_seqr_project_url(project)}|*{project.name}*> (guid: {project.guid})"
    )
    trigger_success = trigger_data_loading(
        [project], individual_ids, sample_type, Sample.DATASET_TYPE_VARIANT_CALLS, project.genome_version, data_path, user=user, success_message=success_message,
        success_slack_channel=SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, error_message=f'ERROR triggering AnVIL loading for project {project.guid}',
    )
    AirtableSession(user, base=AirtableSession.ANVIL_BASE).safe_create_records(
        ANVIL_REQUEST_TRACKING_TABLE, [{
            'Requester Name': user.get_full_name(),
            'Requester Email': user.email,
            'AnVIL Project URL': _get_seqr_project_url(project),
            'Initial Request Date': datetime.now().strftime('%Y-%m-%d'),
            'Number of Samples': len(individual_ids),
            'Status': 'Loading' if trigger_success else 'Loading Requested'
        }])

    return pedigree_json

def _wait_for_service_account_access(user, namespace, name):
    for _ in range(2):
        time.sleep(3)
        if has_service_account_access(user, namespace, name):
            return True
    raise TerraAPIException('Failed to grant seqr service account access to the workspace', 400)

def _get_seqr_project_url(project):
    return f'{BASE_URL}project/{project.guid}/project_page'
