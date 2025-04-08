import base64
from collections import defaultdict
from datetime import datetime
import gzip
import json
import os
import re
import requests
import urllib3

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied
from django.db.models import Max, F, Q
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError as RequestConnectionError

from seqr.utils.communication_utils import send_project_notification
from seqr.utils.search.add_data_utils import prepare_data_loading_request, get_loading_samples_validator
from seqr.utils.search.utils import get_search_backend_status, delete_search_backend_data
from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.vcf_utils import validate_vcf_and_get_samples, get_vcf_list

from seqr.views.utils.airflow_utils import trigger_airflow_data_loading, trigger_airflow_dag, is_airflow_enabled
from seqr.views.utils.airtable_utils import AirtableSession, LOADABLE_PDO_STATUSES, AVAILABLE_PDO_STATUS
from seqr.views.utils.dataset_utils import load_rna_seq, load_phenotype_prioritization_data_file, RNA_DATA_TYPE_CONFIGS, \
    post_process_rna_data, convert_django_meta_to_http_headers
from seqr.views.utils.file_utils import parse_file, get_temp_file_path, load_uploaded_file, persist_temp_file
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.pedigree_info_utils import get_validated_related_individuals, JsonConstants
from seqr.views.utils.permissions_utils import data_manager_required, pm_or_data_manager_required, get_internal_projects
from seqr.views.utils.terra_api_utils import anvil_enabled

from seqr.models import Sample, RnaSample, Individual, Project, PhenotypePrioritization

from settings import KIBANA_SERVER, KIBANA_ELASTICSEARCH_PASSWORD, KIBANA_ELASTICSEARCH_USER, \
    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, LOADING_DATASETS_DIR, PIPELINE_RUNNER_SERVER, \
    LUIGI_UI_SERVICE_HOSTNAME, LUIGI_UI_SERVICE_PORT

logger = SeqrLogger(__name__)


@data_manager_required
def elasticsearch_status(request):
    return create_json_response(get_search_backend_status())


@data_manager_required
def delete_index(request):
    index = json.loads(request.body)['index']
    updated_indices = delete_search_backend_data(index)

    return create_json_response({'indices': updated_indices})

@pm_or_data_manager_required
def update_rna_seq(request):
    request_json = json.loads(request.body)

    data_type = request_json['dataType']
    file_path = request_json['file']
    if not does_file_exist(file_path, user=request.user):
        return create_json_response({'error': 'File not found: {}'.format(file_path)}, status=400)

    mapping_file = None
    uploaded_mapping_file_id = request_json.get('mappingFile', {}).get('uploadedFileId')
    if uploaded_mapping_file_id:
        mapping_file = load_uploaded_file(uploaded_mapping_file_id)

    file_name_prefix = f'rna_sample_data__{data_type}__{datetime.now().isoformat()}'
    file_dir = get_temp_file_path(file_name_prefix, is_local=True)
    os.mkdir(file_dir)

    sample_files = {}

    def _save_sample_data(sample_key, sample_data):
        if sample_key not in sample_files:
            file_name = _get_sample_file_path(file_dir, '_'.join(sample_key))
            sample_files[sample_key] = gzip.open(file_name, 'at')
        sample_files[sample_key].write(f'{json.dumps(sample_data)}\n')

    try:
        sample_guids_to_keys, info, warnings = load_rna_seq(
            data_type, file_path, _save_sample_data,
            user=request.user, mapping_file=mapping_file, ignore_extra_samples=request_json.get('ignoreExtraSamples'))
    except ValueError as e:
        return create_json_response({'error': str(e)}, status=400)

    for sample_guid, sample_key in sample_guids_to_keys.items():
        sample_files[sample_key].close()  # Required to ensure gzipped files are properly terminated
        os.rename(
            _get_sample_file_path(file_dir, '_'.join(sample_key)),
            _get_sample_file_path(file_dir, sample_guid),
        )

    if sample_guids_to_keys:
        persist_temp_file(file_name_prefix, request.user)

    return create_json_response({
        'info': info,
        'warnings': warnings,
        'fileName': file_name_prefix,
        'sampleGuids': sorted(sample_guids_to_keys.keys()),
    })


def _get_sample_file_path(file_dir, sample_guid):
    return os.path.join(file_dir, f'{sample_guid}.json.gz')


@pm_or_data_manager_required
def load_rna_seq_sample_data(request, sample_guid):
    sample = RnaSample.objects.get(guid=sample_guid)
    logger.info(f'Loading outlier data for {sample.individual.individual_id}', request.user)

    request_json = json.loads(request.body)
    file_name = request_json['fileName']
    data_type = request_json['dataType']
    config = RNA_DATA_TYPE_CONFIGS[data_type]

    file_path = get_temp_file_path(f'{file_name}/{sample_guid}.json.gz')
    if does_file_exist(file_path, user=request.user):
        data_rows = [json.loads(line) for line in file_iter(file_path, user=request.user)]
        data_rows, error = post_process_rna_data(sample_guid, data_rows, **config.get('post_process_kwargs', {}))
    else:
        logger.error(f'No saved temp data found for {sample_guid} with file prefix {file_name}', request.user)
        error = 'Data for this sample was not properly parsed. Please re-upload the data'
    if error:
        return create_json_response({'error': error}, status=400)

    model_cls = config['model_class']
    model_cls.bulk_create(request.user, [model_cls(sample=sample, **data) for data in data_rows], batch_size=1000)
    update_model_from_json(sample, {'is_active': True}, user=request.user)

    return create_json_response({'success': True})


def _notify_phenotype_prioritization_loaded(project, tool, num_samples):
    send_project_notification(
        project,
        notification=f'{num_samples} {tool.title()} sample(s)',
        subject=f'New {tool.title()} data available in seqr',
    )


@data_manager_required
def load_phenotype_prioritization_data(request):
    request_json = json.loads(request.body)

    file_path = request_json['file']
    if not does_file_exist(file_path, user=request.user):
        return create_json_response({'error': 'File not found: {}'.format(file_path)}, status=400)

    try:
        tool, data_by_project_indiv_id = load_phenotype_prioritization_data_file(file_path, request.user)
    except ValueError as e:
        return create_json_response({'error': str(e)}, status=400)

    info = [f'Loaded {tool.title()} data from {file_path}']

    internal_projects = get_internal_projects().filter(name__in=data_by_project_indiv_id)
    projects_by_name = {p_name: [project for project in internal_projects if project.name == p_name]
                       for p_name in data_by_project_indiv_id.keys()}
    missing_projects = [p_name for p_name, projects in projects_by_name.items() if len(projects) == 0]
    missing_info = f"Project {', '.join(missing_projects)} not found. " if missing_projects else ''
    conflict_projects = [p_name for p_name, projects in projects_by_name.items() if len(projects) > 1]
    conflict_info = f"Projects with conflict name(s) {', '.join(conflict_projects)}." if conflict_projects else ''

    if missing_info or conflict_info:
        return create_json_response({'error': missing_info + conflict_info}, status=400)

    all_records_by_project_name = {}
    to_delete = PhenotypePrioritization.objects.none()
    error = None
    for project_name, records_by_indiv in data_by_project_indiv_id.items():
        indivs = Individual.objects.filter(family__project=projects_by_name[project_name][0],
                                           individual_id__in=records_by_indiv.keys())
        existing_indivs_by_id = {ind.individual_id: ind for ind in indivs}

        missing_individuals = set(records_by_indiv.keys()) - set(existing_indivs_by_id.keys())
        if missing_individuals:
            error = f"Can't find individuals {', '.join(sorted(list(missing_individuals)))}"
            break
        indiv_records = []
        for sample_id, records in records_by_indiv.items():
            for rec in records:
                rec['individual'] = existing_indivs_by_id[sample_id]
                indiv_records.append(rec)

        exist_records = PhenotypePrioritization.objects.filter(tool=tool, individual__in=indivs)

        delete_info = f'deleted {len(exist_records)} record(s), ' if exist_records else ''
        info.append(f'Project {project_name}: {delete_info}loaded {len(indiv_records)} record(s)')

        to_delete |= exist_records
        all_records_by_project_name[project_name] = indiv_records

    if error:
        return create_json_response({'error': error}, status=400)

    if to_delete:
        PhenotypePrioritization.bulk_delete(request.user, to_delete)

    models_to_create = [
        PhenotypePrioritization(**record) for records in all_records_by_project_name.values() for record in records
    ]
    PhenotypePrioritization.bulk_create(request.user, models_to_create)

    for project_name, indiv_records in all_records_by_project_name.items():
        project = projects_by_name[project_name][0]
        num_samples = len(indiv_records)
        _notify_phenotype_prioritization_loaded(project, tool, num_samples)

    return create_json_response({
        'info': info,
        'success': True
    })


AVAILABLE_PDO_STATUSES = {
    AVAILABLE_PDO_STATUS,
    'Historic',
}


@pm_or_data_manager_required
def loading_vcfs(request):
    if anvil_enabled():
        raise PermissionDenied()
    return create_json_response({
        'vcfs': get_vcf_list(LOADING_DATASETS_DIR, request.user),
    })


@pm_or_data_manager_required
def validate_callset(request):
    request_json = json.loads(request.body)
    dataset_type = request_json['datasetType'] if anvil_enabled() else None
    samples = validate_vcf_and_get_samples(
        _callset_path(request_json), request.user, request_json['genomeVersion'], dataset_type=dataset_type,
        path_name=request_json['filePath'],
    )
    return create_json_response({'vcfSamples': samples})


def _callset_path(request_json):
    file_path = request_json['filePath']
    if not AirtableSession.is_airtable_enabled():
        file_path = os.path.join(LOADING_DATASETS_DIR, file_path.lstrip('/'))
    return file_path


@pm_or_data_manager_required
def get_loaded_projects(request, genome_version, sample_type, dataset_type):
    projects = get_internal_projects().filter(is_demo=False, genome_version=genome_version)
    project_samples = None
    if AirtableSession.is_airtable_enabled():
        try:
            project_samples = _fetch_airtable_loadable_project_samples(request.user, dataset_type, sample_type)
        except ValueError as e:
            return create_json_response({'error': str(e)}, status=400)
        projects = projects.filter(guid__in=project_samples.keys())
    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        exclude_sample_type = Sample.SAMPLE_TYPE_WES if sample_type == Sample.SAMPLE_TYPE_WGS else Sample.SAMPLE_TYPE_WGS
        # Include projects with either the matched sample type OR with no loaded data
        projects = projects.exclude(family__individual__sample__sample_type=exclude_sample_type)
    else:
        # All other data types can only be loaded to projects which already have loaded data
        projects = projects.filter(family__individual__sample__sample_type=sample_type)

    projects = projects.distinct().order_by('name').values('name', projectGuid=F('guid'), dataTypeLastLoaded=Max(
        'family__individual__sample__loaded_date',
        filter=Q(family__individual__sample__dataset_type=dataset_type) & Q(family__individual__sample__sample_type=sample_type),
    ))

    if project_samples:
        for project in projects:
            project['sampleIds'] = sorted(project_samples[project['projectGuid']])

    return create_json_response({'projects': list(projects)})


AIRTABLE_CALLSET_FIELDS = {
    (Sample.DATASET_TYPE_MITO_CALLS, Sample.SAMPLE_TYPE_WES): 'MITO_WES_CallsetPath',
    (Sample.DATASET_TYPE_MITO_CALLS, Sample.SAMPLE_TYPE_WGS): 'MITO_WGS_CallsetPath',
    (Sample.DATASET_TYPE_SV_CALLS, Sample.SAMPLE_TYPE_WES): 'gCNV_CallsetPath',
    (Sample.DATASET_TYPE_SV_CALLS, Sample.SAMPLE_TYPE_WGS): 'SV_CallsetPath',
}


def _get_dataset_type_samples_for_matched_pdos(pdo_statuses, user, dataset_type, sample_type, **kwargs):
    required_sample_fields = ['PassingCollaboratorSampleIDs']
    required_data_type_field = AIRTABLE_CALLSET_FIELDS.get((dataset_type, sample_type))
    if required_data_type_field:
        required_sample_fields.append(required_data_type_field)
    return AirtableSession(user).get_samples_for_matched_pdos(
        pdo_statuses, required_sample_fields=required_sample_fields, **kwargs,
    ).values()


def _fetch_airtable_loadable_project_samples(user, dataset_type, sample_type):
    samples = _get_dataset_type_samples_for_matched_pdos(LOADABLE_PDO_STATUSES, user, dataset_type, sample_type)
    project_samples = defaultdict(set)
    for sample in samples:
        for pdo in sample['pdos']:
            project_samples[pdo['project_guid']].add(sample['sample_id'])
    return project_samples


@pm_or_data_manager_required
def load_data(request):
    request_json = json.loads(request.body)
    vcf_samples = request_json['vcfSamples']
    sample_type = request_json['sampleType']
    dataset_type = request_json.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS)
    projects = [json.loads(project) for project in request_json['projects']]
    project_samples = {p['projectGuid']: p.get('sampleIds') for p in projects}

    projects_by_guid = {p.guid: p for p in Project.objects.filter(guid__in=project_samples)}
    if len(projects_by_guid) < len(projects):
        missing = sorted(set(project_samples.keys()) - set(projects_by_guid.keys()))
        return create_json_response({'error': f'The following projects are invalid: {", ".join(missing)}'}, status=400)

    errors = []
    individual_ids = []
    vcf_sample_id_map = {}
    for project_guid, sample_ids in project_samples.items():
        project_individual_ids, project_vcf_sample_id_map = _get_valid_search_individuals(
            projects_by_guid[project_guid], sample_ids, vcf_samples, dataset_type, sample_type, request.user, errors,
        )
        individual_ids += project_individual_ids
        vcf_sample_id_map.update(project_vcf_sample_id_map)

    if errors:
        raise ErrorsWarningsException(errors)

    loading_args = (
        projects_by_guid.values(), individual_ids, sample_type, dataset_type, request_json['genomeVersion'], _callset_path(request_json),
    )
    loading_kwargs = {
        'user': request.user,
        'skip_validation': request_json.get('skipValidation', False),
        'skip_check_sex_and_relatedness': request_json.get('skipSRChecks', False),
    }
    if AirtableSession.is_airtable_enabled():
        success_message = f'*{request.user.email}* triggered loading internal {sample_type} {dataset_type} data for {len(projects)} projects'
        error_message = f'ERROR triggering internal {sample_type} {dataset_type} loading'
        trigger_airflow_data_loading(
            *loading_args, **loading_kwargs, success_message=success_message, error_message=error_message,
            success_slack_channel=SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, is_internal=True, vcf_sample_id_map=vcf_sample_id_map,
        )
    else:
        request_json, _ = prepare_data_loading_request(
            *loading_args, **loading_kwargs, pedigree_dir=LOADING_DATASETS_DIR, raise_pedigree_error=True,
        )
        response = requests.post(f'{PIPELINE_RUNNER_SERVER}/loading_pipeline_enqueue', json=request_json, timeout=60)
        if response.status_code == 409:
            raise ErrorsWarningsException(['Loading pipeline is already running. Wait for it to complete and resubmit'])
        response.raise_for_status()
        logger.info('Triggered loading pipeline', request.user, detail=request_json)

    return create_json_response({'success': True})


def _get_valid_search_individuals(project, airtable_samples, vcf_samples, dataset_type, sample_type, user, errors):
    loading_samples = set(airtable_samples or vcf_samples)
    search_individuals_by_id = {
        i[JsonConstants.INDIVIDUAL_ID_COLUMN]: i for i in
        Individual.objects.filter(family__project=project, individual_id__in=loading_samples).values(
            'id', JsonConstants.AFFECTED_COLUMN,  **{
                JsonConstants.INDIVIDUAL_ID_COLUMN: F('individual_id'),
                JsonConstants.FAMILY_ID_COLUMN: F('family__family_id'),
            },
        )
    }

    fetch_missing_loaded_samples = None
    fetch_missing_vcf_samples = None
    vcf_sample_id_map = {}
    sample_source = 'the vcf'
    if airtable_samples:
        get_sample_kwargs = {
            'user': user, 'dataset_type': dataset_type, 'sample_type': sample_type, 'project_guid': project.guid,
        }
        fetch_missing_loaded_samples = lambda: {
            sample['sample_id'] for sample in _get_dataset_type_samples_for_matched_pdos(
                AVAILABLE_PDO_STATUSES, **get_sample_kwargs,
            )
        }
        def fetch_missing_vcf_samples(missing_vcf_samples):
            samples = _get_dataset_type_samples_for_matched_pdos(
                LOADABLE_PDO_STATUSES + AVAILABLE_PDO_STATUSES, additional_sample_fields=['VCFIDWithMismatch'],
                or_filters={'VCFIDWithMismatch': missing_vcf_samples}, **get_sample_kwargs,
            )
            vcf_sample_id_map.update({
                s['sample_id']: s['VCFIDWithMismatch'] for s in samples if s['sample_id'] in airtable_samples
            })
            return vcf_sample_id_map.values()
        sample_source = 'airtable'

        missing_airtable_samples = {sample_id for sample_id in airtable_samples if sample_id not in search_individuals_by_id}
        if missing_airtable_samples:
            errors.append(
                f'The following samples are included in airtable for {project.name} but are missing from seqr: {", ".join(missing_airtable_samples)}')

    loaded_individual_ids = []
    validate_expected_samples = get_loading_samples_validator(
        vcf_samples, loaded_individual_ids, sample_source=sample_source,
        fetch_missing_loaded_samples=fetch_missing_loaded_samples, fetch_missing_vcf_samples=fetch_missing_vcf_samples,
        missing_family_samples_error= f'The following families have previously loaded samples absent from {sample_source}\n',
    )

    get_validated_related_individuals(
        project, search_individuals_by_id, errors, search_dataset_type=dataset_type, search_sample_type=sample_type,
        validate_expected_samples=validate_expected_samples, add_missing_parents=False,
    )

    return [i['id'] for i in search_individuals_by_id.values()] + loaded_individual_ids, vcf_sample_id_map


@data_manager_required
def trigger_dag(request, dag_id):
    if not is_airflow_enabled():
        raise PermissionDenied()
    request_json = json.loads(request.body)
    project_guid = request_json.pop('project', None)
    family_guid = request_json.pop('family', None)
    kwargs = {_to_snake_case(k): v for k, v in request_json.items()}
    project = None
    if project_guid:
        project = Project.objects.get(guid=project_guid)
    elif family_guid:
        project = Project.objects.get(family__guid=family_guid)
        kwargs['family_guids'] = [family_guid]
    try:
        dag_variables = trigger_airflow_dag(dag_id, project, **kwargs)
    except Exception as e:
        return create_json_response({'error': str(e)}, status=400)
    return create_json_response({'info': [f'Triggered DAG {dag_id} with variables: {json.dumps(dag_variables)}']})


# Hop-by-hop HTTP response headers shouldn't be forwarded.
# More info at: http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
EXCLUDE_HTTP_RESPONSE_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate',
    'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade',
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@data_manager_required
@csrf_exempt
def proxy_to_kibana(request):
    headers = {}
    if KIBANA_ELASTICSEARCH_PASSWORD:
        token = base64.b64encode('{}:{}'.format(KIBANA_ELASTICSEARCH_USER, KIBANA_ELASTICSEARCH_PASSWORD).encode('utf-8'))
        headers['Authorization'] = 'Basic {}'.format(token.decode('utf-8'))
    return _proxy_iframe_page(request, 'Kibana', KIBANA_SERVER, additional_headers=headers)


def _proxy_iframe_page(request, page_name, host, additional_headers=None, path_prefix=None):
    headers = convert_django_meta_to_http_headers(request)
    headers['Host'] = host
    headers.update(additional_headers or {})

    path = request.get_full_path()
    if path_prefix:
        path = path.replace(path_prefix, '')
    url = f'http://{host}{path}'

    request_method = getattr(requests.Session(), request.method.lower())

    try:
        # use stream=True because kibana returns gziped responses, and this prevents the requests module from
        # automatically unziping them
        response = request_method(url, headers=headers, data=request.body, stream=True, verify=True)
        response_content = response.raw.read()
        # make sure the connection is released back to the connection pool
        # (based on http://docs.python-requests.org/en/master/user/advanced/#body-content-workflow)
        response.close()

        proxy_response = HttpResponse(
            content=response_content,
            status=response.status_code,
            reason=response.reason,
            charset=response.encoding
        )

        for key, value in response.headers.items():
            if key.lower() not in EXCLUDE_HTTP_RESPONSE_HEADERS:
                proxy_response[key.title()] = value

        return proxy_response
    except (ConnectionError, RequestConnectionError) as e:
        logger.error(str(e), request.user)
        return HttpResponse(f'Error: Unable to connect to {page_name} {e}', status=400)


@data_manager_required
def proxy_to_luigi(request):
    if not LUIGI_UI_SERVICE_HOSTNAME:
        return HttpResponse('Loading Pipeline UI is not configured', status=404)
    return _proxy_iframe_page(
        request, 'Luigi UI', f'{LUIGI_UI_SERVICE_HOSTNAME}:{LUIGI_UI_SERVICE_PORT}', path_prefix='/luigi_ui',
    )
