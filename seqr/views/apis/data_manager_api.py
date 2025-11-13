import base64
from collections import defaultdict
import json
import os
import requests
import urllib3

from django.core.exceptions import PermissionDenied
from django.db.models import Max, F, Q
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError as RequestConnectionError

from clickhouse_search.search import delete_clickhouse_project
from seqr.utils.communication_utils import send_project_notification
from seqr.utils.search.add_data_utils import trigger_data_loading, get_missing_family_samples, get_loaded_individual_ids, trigger_delete_families_search
from seqr.utils.search.elasticsearch.es_utils import get_elasticsearch_status, delete_es_index
from seqr.utils.search.utils import clickhouse_only, es_only, InvalidSearchException
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.vcf_utils import validate_vcf_and_get_samples, get_vcf_list

from seqr.views.utils.airtable_utils import AirtableSession, LOADABLE_PDO_STATUSES, AVAILABLE_PDO_STATUS
from seqr.views.utils.dataset_utils import load_rna_seq, load_phenotype_prioritization_data_file, convert_django_meta_to_http_headers
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.pedigree_info_utils import get_validated_related_individuals, JsonConstants
from seqr.views.utils.permissions_utils import data_manager_required, pm_or_data_manager_required, get_internal_projects
from seqr.views.utils.terra_api_utils import anvil_enabled

from seqr.models import Sample, RnaSample, Individual, Project, PhenotypePrioritization

from settings import KIBANA_SERVER, KIBANA_ELASTICSEARCH_PASSWORD, KIBANA_ELASTICSEARCH_USER, \
    LOADING_DATASETS_DIR, LUIGI_UI_SERVICE_HOSTNAME, LUIGI_UI_SERVICE_PORT

logger = SeqrLogger(__name__)


@data_manager_required
@es_only
def elasticsearch_status(request):
    return create_json_response(get_elasticsearch_status())


@data_manager_required
@es_only
def delete_index(request):
    index = json.loads(request.body)['index']
    active_samples = Sample.objects.filter(is_active=True, elasticsearch_index=index)
    if active_samples:
        projects = set(active_samples.values_list('individual__family__project__name', flat=True))
        raise InvalidSearchException(f'"{index}" is still used by: {", ".join(projects)}')

    updated_indices =  delete_es_index(index)

    return create_json_response({'indices': updated_indices})

RNA = 'RNA'
TISSUE_FIELD = 'TissueOfOrigin'
AIRTABLE_TISSUE_TYPE_MAP = {
    'whole_blood': 'Blood',
    'fibroblasts': 'Fibroblast',
    'muscle':  'Muscle',
    'airway_cultured_epithelium': 'Nasal Epithelium',
    'brain': 'Brain',
}
TISSUE_TYPE_MAP = {
    AIRTABLE_TISSUE_TYPE_MAP[name]: type
    for type, name in RnaSample.TISSUE_TYPE_CHOICES if name in AIRTABLE_TISSUE_TYPE_MAP
}

@pm_or_data_manager_required
def update_rna_seq(request):
    request_json = json.loads(request.body)

    airtable_samples = _get_dataset_type_samples_for_matched_pdos(
        ['RNA ready to load'], request.user, RNA, None, sample_fields=[TISSUE_FIELD], skip_invalid_pdos=True,
    )
    sample_metadata_mapping = {
        sample['sample_id']: {
            'tissue': TISSUE_TYPE_MAP[sample[TISSUE_FIELD][0]],
            'project_guid': sample['pdos'][0]['project_guid'],
            'sample_id': sample.get('CollaboratorSampleID') or sample['sample_id'],
        }
        for sample in airtable_samples if len(sample[TISSUE_FIELD]) == 1 and len(sample['pdos']) == 1
    }
    misconfigured_samples = [s['sample_id'] for s in airtable_samples if s['sample_id'] not in sample_metadata_mapping]
    if misconfigured_samples:
        logger.warning(f'Skipping samples associated with multiple conflicting PDOs in Airtable: {", ".join(sorted(misconfigured_samples))}', request.user)

    response_json, status = load_rna_seq(request_json, request.user, sample_metadata_mapping=sample_metadata_mapping)
    return create_json_response(response_json, status=status)


def _get_sample_file_path(file_dir, sample_guid):
    return os.path.join(file_dir, f'{sample_guid}.json.gz')


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
    try:
        tool, data_by_project_indiv_id = load_phenotype_prioritization_data_file(file_path, request.user)
    except FileNotFoundError:
        return create_json_response({'error': 'File not found: {}'.format(file_path)}, status=400)
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


AVAILABLE_PDO_STATUSES = [
    AVAILABLE_PDO_STATUS,
    'Historic',
]


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
    (RNA, None): TISSUE_FIELD,
}


def _get_dataset_type_samples_for_matched_pdos(pdo_statuses, user, dataset_type, sample_type=None, **kwargs):
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
    project_counts = []
    vcf_sample_id_map = {}
    for project_guid, sample_ids in project_samples.items():
        project_individual_ids, project_vcf_sample_id_map = _get_valid_search_individuals(
            projects_by_guid[project_guid], sample_ids, vcf_samples, dataset_type, sample_type, request.user, errors,
        )
        individual_ids += project_individual_ids
        vcf_sample_id_map.update(project_vcf_sample_id_map)
        project_counts.append(f'{projects_by_guid[project_guid].name}: {len(project_individual_ids)}')

    if errors:
        raise ErrorsWarningsException(errors)

    is_local = True
    success_message = None
    error_message = None
    if AirtableSession.is_airtable_enabled():
        is_local = False
        success_message = f'*{request.user.email}* triggered loading internal {sample_type} {dataset_type} data for {len(individual_ids)} samples in {len(projects)} projects ({"; ".join(sorted(project_counts))})'
        error_message = f'ERROR triggering internal {sample_type} {dataset_type} loading'

    success = trigger_data_loading(
        projects_by_guid.values(), individual_ids, sample_type, dataset_type, request_json['genomeVersion'],
        _callset_path(request_json), user=request.user,
        skip_check_sex_and_relatedness=request_json.get('skipSRChecks', False), vcf_sample_id_map=vcf_sample_id_map,
        raise_error=is_local, skip_expect_tdr_metrics=is_local, success_message=success_message, error_message=error_message,
    )

    return create_json_response({'success': success})


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

    if airtable_samples:
        missing_airtable_samples = {sample_id for sample_id in airtable_samples if sample_id not in search_individuals_by_id}
        if missing_airtable_samples:
            errors.append(
                f'The following samples are included in airtable for {project.name} but are missing from seqr: {", ".join(missing_airtable_samples)}')

    previous_loaded_individuals, record_family_ids, _ = get_validated_related_individuals(
        project, search_individuals_by_id, errors, search_dataset_type=dataset_type, search_sample_type=sample_type,
        add_missing_parents=False,
    )

    expected_sample_set = record_family_ids if airtable_samples else vcf_samples
    missing_samples_by_family = get_missing_family_samples(expected_sample_set, record_family_ids, previous_loaded_individuals.values())
    loading_samples = set(record_family_ids.keys())
    get_sample_kwargs = {
        'user': user, 'dataset_type': dataset_type, 'sample_type': sample_type, 'project_guid': project.guid,
    }
    if missing_samples_by_family and airtable_samples:
        try:
            additional_loaded_samples = {
                sample['sample_id'] for sample in _get_dataset_type_samples_for_matched_pdos(
                    AVAILABLE_PDO_STATUSES, **get_sample_kwargs,
                )
            }
            for missing_samples in missing_samples_by_family.values():
                loading_samples.update(missing_samples.intersection(additional_loaded_samples))
                missing_samples -= additional_loaded_samples
            missing_samples_by_family = {
                family_id: samples for family_id, samples in missing_samples_by_family.items() if samples
            }
        except ValueError as e:
            errors.append(str(e))

    sample_source = 'airtable' if airtable_samples else 'the vcf'
    if missing_samples_by_family:
        missing_family_sample_messages = [
            f'Family {family_id}: {", ".join(sorted(individual_ids))}'
            for family_id, individual_ids in missing_samples_by_family.items()
        ]
        errors.append('\n'.join(
            [f'The following families have previously loaded samples absent from {sample_source}'] +
            sorted(missing_family_sample_messages)
        ))

    vcf_sample_id_map = {}
    missing_vcf_samples = [] if vcf_samples is None else set(loading_samples - set(vcf_samples))
    if missing_vcf_samples and airtable_samples:
        try:
            samples = _get_dataset_type_samples_for_matched_pdos(
                LOADABLE_PDO_STATUSES + AVAILABLE_PDO_STATUSES, **get_sample_kwargs, sample_fields=['VCFIDWithMismatch'],
                additional_sample_filters={'SeqrIDWithMismatch': sorted(missing_vcf_samples)},
            )
            vcf_sample_id_map.update({
                s['sample_id']: s['VCFIDWithMismatch'] for s in samples
                if s['sample_id'] in airtable_samples and s['VCFIDWithMismatch'] in vcf_samples
            })
            missing_vcf_samples -= set(vcf_sample_id_map.keys())
        except ValueError as e:
            errors.append(str(e))
    if missing_vcf_samples:
        errors.append(
            f'The following samples are included in {sample_source} but are missing from the VCF: {", ".join(sorted(missing_vcf_samples))}',
        )

    loaded_individual_ids = get_loaded_individual_ids(record_family_ids, previous_loaded_individuals.values())

    return [i['id'] for i in search_individuals_by_id.values()] + loaded_individual_ids, vcf_sample_id_map


@data_manager_required
@clickhouse_only
def trigger_delete_project(request):
    request_json = json.loads(request.body)
    project_guid = request_json.pop('project')
    dataset_type = request_json.get('datasetType')
    project = Project.objects.get(guid=project_guid)
    samples = Sample.objects.filter(individual__family__project=project, dataset_type=dataset_type, is_active=True)
    sample_types = list(
        samples.values_list('sample_type', flat=True).distinct()
    ) if dataset_type == Sample.DATASET_TYPE_SV_CALLS else [None]
    updated = Sample.bulk_update(user=request.user, update_json={'is_active': False}, queryset=samples)
    info = [f'Deactivated search for {len(updated)} individuals']
    for sample_type in sample_types:
        info.append(delete_clickhouse_project(project, dataset_type=dataset_type, sample_type=sample_type))
    return create_json_response({'info': info})


@data_manager_required
@clickhouse_only
def trigger_delete_family(request):
    request_json = json.loads(request.body)
    family_guid = request_json.pop('family')
    project = Project.objects.get(family__guid=family_guid)
    samples = Sample.objects.filter(individual__family__guid=family_guid)
    info = trigger_delete_families_search(project, [family_guid], request.user)
    return create_json_response({'info': info})


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
