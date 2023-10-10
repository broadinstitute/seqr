import base64
from collections import defaultdict, OrderedDict
from datetime import datetime
import gzip
import itertools
import json
import os
import re
import requests
import urllib3

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Max, Value, F, Q
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError as RequestConnectionError

from seqr.utils.search.utils import get_search_backend_status, delete_search_backend_data
from seqr.utils.search.constants import SEQR_DATSETS_GS_PATH
from seqr.utils.file_utils import file_iter, does_file_exist, get_gs_file_list
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.vcf_utils import validate_vcf_exists

from seqr.views.utils.airflow_utils import trigger_data_loading
from seqr.views.utils.dataset_utils import load_rna_seq_outlier, load_rna_seq_tpm, load_phenotype_prioritization_data_file, \
    load_rna_seq_splice_outlier
from seqr.views.utils.export_utils import write_multiple_files_to_gs
from seqr.views.utils.file_utils import parse_file, get_temp_upload_directory, load_uploaded_file
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import data_manager_required, pm_or_data_manager_required, get_internal_projects

from seqr.models import Sample, Individual, Project, RnaSeqOutlier, RnaSeqTpm, PhenotypePrioritization, RnaSeqSpliceOutlier

from settings import KIBANA_SERVER, KIBANA_ELASTICSEARCH_PASSWORD, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)


@data_manager_required
def elasticsearch_status(request):
    return create_json_response(get_search_backend_status())


@data_manager_required
def delete_index(request):
    index = json.loads(request.body)['index']
    updated_indices = delete_search_backend_data(index)

    return create_json_response({'indices': updated_indices})


@data_manager_required
def upload_qc_pipeline_output(request):
    file_path = json.loads(request.body)['file'].strip()
    if not does_file_exist(file_path, user=request.user):
        return create_json_response({'errors': ['File not found: {}'.format(file_path)]}, status=400)
    raw_records = parse_file(file_path, file_iter(file_path, user=request.user))

    json_records = [dict(zip(raw_records[0], row)) for row in raw_records[1:]]

    try:
        dataset_type, data_type, records_by_sample_id = _parse_raw_qc_records(json_records)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400, reason=str(e))

    info_message = 'Parsed {} {} samples'.format(
        len(json_records), 'SV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else data_type)
    logger.info(info_message, request.user)
    info = [info_message]
    warnings = []

    samples = Sample.objects.filter(
        sample_id__in=records_by_sample_id.keys(),
        sample_type=Sample.SAMPLE_TYPE_WES if data_type == 'exome' else Sample.SAMPLE_TYPE_WGS,
        dataset_type=dataset_type,
    ).exclude(
        individual__family__project__name__in=EXCLUDE_PROJECTS
    ).exclude(individual__family__project__is_demo=True)

    sample_individuals = {
        agg['sample_id']: agg['individuals'] for agg in
        samples.values('sample_id').annotate(individuals=ArrayAgg('individual_id', distinct=True))
    }

    sample_individual_max_loaded_date = {
        agg['individual_id']: agg['max_loaded_date'] for agg in
        samples.values('individual_id').annotate(max_loaded_date=Max('loaded_date'))
    }
    individual_latest_sample_id = {
        s.individual_id: s.sample_id for s in samples
        if s.loaded_date == sample_individual_max_loaded_date.get(s.individual_id)
    }

    for sample_id, record in records_by_sample_id.items():
        record['individual_ids'] = list({
            individual_id for individual_id in sample_individuals.get(sample_id, [])
            if individual_latest_sample_id[individual_id] == sample_id
        })

    missing_sample_ids = {sample_id for sample_id, record in records_by_sample_id.items() if not record['individual_ids']}
    if missing_sample_ids:
        individuals = Individual.objects.filter(individual_id__in=missing_sample_ids).exclude(
            family__project__name__in=EXCLUDE_PROJECTS).exclude(
            family__project__is_demo=True).filter(
            sample__sample_type=Sample.SAMPLE_TYPE_WES if data_type == 'exome' else Sample.SAMPLE_TYPE_WGS).distinct()
        individual_db_ids_by_id = defaultdict(list)
        for individual in individuals:
            individual_db_ids_by_id[individual.individual_id].append(individual.id)
        for sample_id, record in records_by_sample_id.items():
            if not record['individual_ids'] and len(individual_db_ids_by_id[sample_id]) >= 1:
                record['individual_ids'] = individual_db_ids_by_id[sample_id]
                missing_sample_ids.remove(sample_id)

    multi_individual_samples = {
        sample_id: len(record['individual_ids']) for sample_id, record in records_by_sample_id.items()
        if len(record['individual_ids']) > 1}
    if multi_individual_samples:
        logger.warning('Found {} multi-individual samples from qc output'.format(len(multi_individual_samples)),
                    request.user)
        warnings.append('The following {} samples were added to multiple individuals: {}'.format(
            len(multi_individual_samples), ', '.join(
                sorted(['{} ({})'.format(sample_id, count) for sample_id, count in multi_individual_samples.items()]))))

    if missing_sample_ids:
        logger.warning('Missing {} samples from qc output'.format(len(missing_sample_ids)), request.user)
        warnings.append('The following {} samples were skipped: {}'.format(
            len(missing_sample_ids), ', '.join(sorted(list(missing_sample_ids)))))

    records_with_individuals = [
        record for sample_id, record in records_by_sample_id.items() if sample_id not in missing_sample_ids
    ]

    if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
        _update_individuals_sv_qc(records_with_individuals, request.user)
    else:
        _update_individuals_variant_qc(records_with_individuals, data_type, warnings, request.user)

    message = 'Found and updated matching seqr individuals for {} samples'.format(len(json_records) - len(missing_sample_ids))
    info.append(message)

    return create_json_response({
        'errors': [],
        'warnings': warnings,
        'info': info,
    })

SV_WES_FALSE_FLAGS = {'lt100_raw_calls': 'raw_calls:_>100', 'lt10_highQS_rare_calls': 'high_QS_rare_calls:_>10'}
SV_WGS_FALSE_FLAGS = {'expected_num_calls': 'outlier_num._calls'}
SV_FALSE_FLAGS = {}
SV_FALSE_FLAGS.update(SV_WES_FALSE_FLAGS)
SV_FALSE_FLAGS.update(SV_WGS_FALSE_FLAGS)

def _parse_raw_qc_records(json_records):
    # Parse SV WES QC
    if all(field in json_records[0] for field in ['sample'] + list(SV_WES_FALSE_FLAGS.keys())):
        records_by_sample_id = {
            re.search('(\d+)_(?P<sample_id>.+)_v\d_Exome_GCP', record['sample']).group('sample_id'): record
            for record in json_records}
        return Sample.DATASET_TYPE_SV_CALLS, 'exome', records_by_sample_id

    # Parse SV WGS QC
    if all(field in json_records[0] for field in ['sample'] + list(SV_WGS_FALSE_FLAGS.keys())):
        return Sample.DATASET_TYPE_SV_CALLS, 'genome', {record['sample']: record for record in json_records}

    # Parse regular variant QC
    missing_columns = [field for field in ['seqr_id', 'data_type', 'filter_flags', 'qc_metrics_filters', 'qc_pop']
                       if field not in json_records[0]]
    if missing_columns:
        raise ValueError('The following required columns are missing: {}'.format(', '.join(missing_columns)))

    data_types = {record['data_type'].lower() for record in json_records if record['data_type'].lower() != 'n/a'}
    if len(data_types) == 0:
        raise ValueError('No data type detected')
    elif len(data_types) > 1:
        raise ValueError('Multiple data types detected: {}'.format(' ,'.join(sorted(data_types))))
    elif list(data_types)[0] not in DATA_TYPE_MAP:
        message = 'Unexpected data type detected: "{}" (should be "exome" or "genome")'.format(list(data_types)[0])
        raise ValueError(message)

    data_type = DATA_TYPE_MAP[list(data_types)[0]]
    records_by_sample_id = {record['seqr_id']: record for record in json_records}

    return Sample.DATASET_TYPE_VARIANT_CALLS, data_type, records_by_sample_id


def _update_individuals_variant_qc(json_records, data_type, warnings, user):
    unknown_filter_flags = set()
    unknown_pop_filter_flags = set()

    inidividuals_by_population = defaultdict(list)
    for record in json_records:
        filter_flags = {}
        for flag in json.loads(record['filter_flags']):
            flag = '{}_{}'.format(flag, data_type) if flag == 'coverage' else flag
            flag_col = FILTER_FLAG_COL_MAP.get(flag, flag)
            if flag_col in record:
                filter_flags[flag] = record[flag_col]
            else:
                unknown_filter_flags.add(flag)

        pop_platform_filters = {}
        for flag in json.loads(record['qc_metrics_filters']):
            flag_col = 'sample_qc.{}'.format(flag)
            if flag_col in record:
                pop_platform_filters[flag] = record[flag_col]
            else:
                unknown_pop_filter_flags.add(flag)

        if filter_flags or pop_platform_filters:
            Individual.bulk_update(user, {
                'filter_flags': filter_flags or None, 'pop_platform_filters': pop_platform_filters or None,
            }, id__in=record['individual_ids'])

        inidividuals_by_population[record['qc_pop'].upper()] += record['individual_ids']

    for population, indiv_ids in inidividuals_by_population.items():
        Individual.bulk_update(user, {'population': population}, id__in=indiv_ids)

    if unknown_filter_flags:
        message = 'The following filter flags have no known corresponding value and were not saved: {}'.format(
            ', '.join(unknown_filter_flags))
        logger.warning(message, user)
        warnings.append(message)

    if unknown_pop_filter_flags:
        message = 'The following population platform filters have no known corresponding value and were not saved: {}'.format(
            ', '.join(unknown_pop_filter_flags))
        logger.warning(message, user)
        warnings.append(message)


def _update_individuals_sv_qc(json_records, user):
    inidividuals_by_qc_flags = defaultdict(list)
    for record in json_records:
        flags = tuple(sorted(flag for field, flag in SV_FALSE_FLAGS.items() if record.get(field) == 'FALSE'))
        inidividuals_by_qc_flags[flags] += record['individual_ids']

    for flags, indiv_ids in inidividuals_by_qc_flags.items():
        Individual.bulk_update(user, {'sv_flags': list(flags) or None}, id__in=indiv_ids)


FILTER_FLAG_COL_MAP = {
    'callrate': 'filtered_callrate',
    'contamination': 'PCT_CONTAMINATION',
    'chimera': 'AL_PCT_CHIMERAS',
    'coverage_exome': 'HS_PCT_TARGET_BASES_20X',
    'coverage_genome': 'WGS_MEAN_COVERAGE'
}

DATA_TYPE_MAP = {
    'exome': 'exome',
    'genome': 'genome',
    'wes': 'exome',
    'wgs': 'genome',
}

EXCLUDE_PROJECTS = [
    '[DISABLED_OLD_CMG_Walsh_WES]', 'Old Engle Lab All Samples 352S', 'Old MEEI Engle Samples',
    'kl_temp_manton_orphan-diseases_cmg-samples_exomes_v1', 'Interview Exomes', 'v02_loading_test_project',
]


RNA_DATA_TYPE_CONFIGS = {
    'outlier': {'load_func': load_rna_seq_outlier, 'model_class': RnaSeqOutlier},
    'tpm': {'load_func': load_rna_seq_tpm, 'model_class': RnaSeqTpm},
    'splice_outlier': {'load_func': load_rna_seq_splice_outlier, 'model_class': RnaSeqSpliceOutlier}
}

@data_manager_required
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

    try:
        load_func = RNA_DATA_TYPE_CONFIGS[data_type]['load_func']
        samples_to_load, info, warnings = load_func(
            file_path, user=request.user, mapping_file=mapping_file, ignore_extra_samples=request_json.get('ignoreExtraSamples'))
    except ValueError as e:
        return create_json_response({'error': str(e)}, status=400)

    # Save sample data for loading
    file_name = f'rna_sample_data__{data_type}__{datetime.now().isoformat()}.json.gz'
    with gzip.open(os.path.join(get_temp_upload_directory(), file_name), 'wt') as f:
        for sample_guid, sample_data in samples_to_load.items():
            f.write(f'{sample_guid}\t\t{json.dumps(sample_data)}\n')

    return create_json_response({
        'info': info,
        'warnings': warnings,
        'fileName': file_name,
        'sampleGuids': list(samples_to_load.keys()),
    })


@data_manager_required
def load_rna_seq_sample_data(request, sample_guid):
    sample = Sample.objects.get(guid=sample_guid)
    logger.info(f'Loading outlier data for {sample.sample_id}', request.user)

    request_json = json.loads(request.body)
    file_name = request_json['fileName']
    data_type = request_json['dataType']
    with gzip.open(os.path.join(get_temp_upload_directory(), file_name), 'rt') as f:
        row = next(line for line in f if line.split('\t\t')[0] == sample_guid)
        data_by_gene = json.loads(row.split('\t\t')[1])

    model_cls = RNA_DATA_TYPE_CONFIGS[data_type]['model_class']
    model_cls.bulk_create(request.user, [model_cls(sample=sample, **data) for data in data_by_gene.values()])

    return create_json_response({'success': True})


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

    all_records = []
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
        all_records += indiv_records

    if error:
        return create_json_response({'error': error}, status=400)

    if to_delete:
        PhenotypePrioritization.bulk_delete(request.user, to_delete)

    PhenotypePrioritization.bulk_create(request.user, [PhenotypePrioritization(**data) for data in all_records])

    return create_json_response({
        'info': info,
        'success': True
    })


@data_manager_required
def write_pedigree(request, project_guid):
    project = Project.objects.get(guid=project_guid)

    possible_file_paths = [
        f'{SEQR_DATSETS_GS_PATH}/{project.get_genome_version_display()}/RDG_{sample_type}_Broad_{callset}/base/projects/{project.guid}'
        for callset, sample_type in itertools.product(['Internal', 'External'], ['WGS', 'WES'])
    ]
    file_path = next((path for path in possible_file_paths if does_file_exist(path)), None)
    if not file_path:
        return create_json_response(
            {'error': f'No {SEQR_DATSETS_GS_PATH} project directory found for {project.guid}'}, status=400,
        )

    annotations = OrderedDict({
        'Project_GUID': Value(project.guid), 'Family_GUID': F('family__guid'), 'Family_ID': F('family__family_id'), 'Individual_ID': F('individual_id'),
        'Paternal_ID': F('father__individual_id'), 'Maternal_ID': F('mother__individual_id'), 'Sex': F('sex'),
    })
    data = Individual.objects.filter(family__project=project).order_by('family_id', 'individual_id').values(**dict(annotations))
    write_multiple_files_to_gs(
        [(f'{project.guid}_pedigree', annotations.keys(), data)],
        file_path, request.user, file_format='tsv')

    return create_json_response({'success': True})


DATA_TYPE_FILE_EXTS = {
    Sample.DATASET_TYPE_MITO_CALLS: ('.mt',),
    Sample.DATASET_TYPE_SV_CALLS: ('.bed',),
}


@pm_or_data_manager_required
def validate_callset(request):
    request_json = json.loads(request.body)
    validate_vcf_exists(
        request_json['filePath'], request.user, allowed_exts=DATA_TYPE_FILE_EXTS.get(request_json['datasetType'])
    )
    return create_json_response({'success': True})


@pm_or_data_manager_required
def get_loaded_projects(request, sample_type, dataset_type):
    projects = get_internal_projects().filter(
        family__individual__sample__sample_type=sample_type, is_demo=False,
    ).distinct().order_by('name').values('name', projectGuid=F('guid'), dataTypeLastLoaded=Max(
        'family__individual__sample__loaded_date', filter=Q(family__individual__sample__dataset_type=dataset_type),
    ))
    return create_json_response({'projects': list(projects)})


@pm_or_data_manager_required
def load_data(request):
    request_json = json.loads(request.body)
    sample_type = request_json['sampleType']
    dataset_type = request_json['datasetType']
    projects = request_json['projects']

    dag_dataset_type = 'GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
        else dataset_type
    dag_name = f'RDG_{sample_type}_Broad_Internal_{dag_dataset_type}'

    version_path_prefix = f'{SEQR_DATSETS_GS_PATH}/GRCh38/{dag_name}'
    version_paths = get_gs_file_list(version_path_prefix, user=request.user, allow_missing=True, check_subfolders=False)
    versions = [re.findall(f'{version_path_prefix}/v(\d\d)/', p) for p in version_paths]
    curr_version = max([int(v[0]) for v in versions if v] + [0])
    dag_variables = {'version_path': f'{version_path_prefix}/v{curr_version+1:02d}'}

    success_message = f'*{request.user.email}* triggered loading internal {sample_type} {dataset_type} data for {len(projects)} projects'
    trigger_data_loading(
        dag_name, projects, request_json['filePath'], dag_variables, request.user, success_message,
        SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, f'ERROR triggering internal {sample_type} {dataset_type} loading',
    )

    return create_json_response({'success': True})


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
    headers = _convert_django_meta_to_http_headers(request.META)
    headers['Host'] = KIBANA_SERVER
    if KIBANA_ELASTICSEARCH_PASSWORD:
        token = base64.b64encode('kibana:{}'.format(KIBANA_ELASTICSEARCH_PASSWORD).encode('utf-8'))
        headers['Authorization'] = 'Basic {}'.format(token.decode('utf-8'))

    url = "http://{host}{path}".format(host=KIBANA_SERVER, path=request.get_full_path())

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
        return HttpResponse("Error: Unable to connect to Kibana {}".format(e), status=400)


def _convert_django_meta_to_http_headers(request_meta_dict):
    """Converts django request.META dictionary into a dictionary of HTTP headers."""

    def convert_key(key):
        # converting Django's all-caps keys (eg. 'HTTP_RANGE') to regular HTTP header keys (eg. 'Range')
        return key.replace("HTTP_", "").replace('_', '-').title()

    http_headers = {
        convert_key(key): str(value).lstrip()
        for key, value in request_meta_dict.items()
        if key.startswith("HTTP_") or (key in ('CONTENT_LENGTH', 'CONTENT_TYPE') and value)
    }

    return http_headers
