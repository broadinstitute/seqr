from collections import defaultdict
import json
import re
import requests

from django.http import StreamingHttpResponse, HttpResponse

from seqr.models import Individual, IgvSample
from seqr.utils.file_utils import file_iter, does_file_exist, is_google_bucket_file_path, run_command, get_google_project
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.json_to_orm_utils import get_or_create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_sample
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    login_and_policies_required, pm_or_data_manager_required, get_project_guids_user_can_view \
    , service_account_access

GS_STORAGE_ACCESS_CACHE_KEY = 'gs_storage_access_cache_entry'
GS_STORAGE_URL = 'https://storage.googleapis.com'
CLOUD_STORAGE_URLS = {
    's3': 'https://s3.amazonaws.com',
    'gs': GS_STORAGE_URL,
}

def _process_alignment_records(rows, num_id_cols=1, **kwargs):
    num_cols = num_id_cols + 1
    invalid_row = next((row for row in rows if not num_cols <= len(row) <= num_cols+1), None)
    if invalid_row:
        raise ValueError(f"Must contain {num_cols} or {num_cols+1} columns: {', '.join(invalid_row)}")
    parsed_records = defaultdict(list)
    for row in rows:
        row_id = row[0] if num_id_cols == 1 else tuple(row[:num_id_cols])
        parsed_records[row_id].append({'filePath': row[num_id_cols], 'sampleId': row[num_cols] if len(row) > num_cols else None})
    return parsed_records


def _post_process_igv_records(individual_dataset_mapping, get_valid_matched_individuals, filename):
    info = []
    all_updates = []

    matched_individuals = get_valid_matched_individuals(individual_dataset_mapping)

    message = f'Parsed {sum([len(rows) for rows in individual_dataset_mapping.values()])} rows in {len(matched_individuals)} individuals'
    if filename:
        message += f' from {filename}'
    info.append(message)

    existing_sample_files = defaultdict(set)
    for sample in IgvSample.objects.select_related('individual').filter(individual__in=matched_individuals.keys()):
        existing_sample_files[sample.individual].add(sample.file_path)

    num_unchanged_rows = 0
    for individual, updates in matched_individuals.items():
        changed_updates = [
            dict(individualGuid=individual.guid, individualId=individual.individual_id, **update)
            for update in updates
            if update['filePath'] not in existing_sample_files[individual]
        ]
        all_updates += changed_updates
        num_unchanged_rows += len(updates) - len(changed_updates)

    if num_unchanged_rows:
        info.append('No change detected for {} rows'.format(num_unchanged_rows))

    return info, all_updates


def _process_igv_table_handler(parse_uploaded_file, get_valid_matched_individuals):
    try:
        uploaded_file_id, filename, individual_dataset_mapping = parse_uploaded_file()

        info, all_updates = _post_process_igv_records(
            individual_dataset_mapping=individual_dataset_mapping,
            get_valid_matched_individuals=get_valid_matched_individuals,
            filename=filename,
        )

        response = {
            'updates': all_updates,
            'uploadedFileId': uploaded_file_id,
            'errors': [],
            'warnings': [],
            'info': info,
        }
        return create_json_response(response)

    except Exception as e:
        return create_json_response({'errors': [str(e)]}, status=400)


@pm_or_data_manager_required
def receive_igv_table_handler(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    def _get_valid_matched_individuals(individual_dataset_mapping):
        matched_individuals = Individual.objects.filter(
            family__project=project, individual_id__in=individual_dataset_mapping.keys()
        )
        unmatched_individuals = set(individual_dataset_mapping.keys()) - {i.individual_id for i in matched_individuals}
        if len(unmatched_individuals) > 0:
            raise Exception('The following Individual IDs do not exist: {}'.format(", ".join(unmatched_individuals)))

        return {i: individual_dataset_mapping[i.individual_id] for i in matched_individuals}

    return _process_igv_table_handler(
        lambda: save_uploaded_file(request, process_records=_process_alignment_records),
        _get_valid_matched_individuals,
    )


@pm_or_data_manager_required
def receive_bulk_igv_table_handler(request):
    def _parse_uploaded_file():
        uploaded_file_id = json.loads(request.body).get('mappingFile', {}).get('uploadedFileId')
        if not uploaded_file_id:
            raise ValueError('No file uploaded')
        records = _process_alignment_records(load_uploaded_file(uploaded_file_id), num_id_cols=2)
        return uploaded_file_id, None, records

    def _get_valid_matched_individuals(individual_dataset_mapping):
        individuals = Individual.objects.filter(
            family__project__guid__in=get_project_guids_user_can_view(request.user, limit_data_manager=False),
            family__project__name__in={k[0] for k in individual_dataset_mapping.keys()},
            individual_id__in={k[1] for k in individual_dataset_mapping.keys()},
        ).select_related('family__project')
        individuals_by_project_id = {(i.family.project.name, i.individual_id): i for i in individuals}
        unmatched = set(individual_dataset_mapping.keys()) - set(individuals_by_project_id.keys())
        if len(unmatched) > 0:
            raise Exception(
                f'The following Individuals do not exist: {", ".join([f"{i} ({p})" for p, i in sorted(unmatched)])}')

        return {v: individual_dataset_mapping[k] for k, v in individuals_by_project_id.items() if individual_dataset_mapping[k]}

    return _process_igv_table_handler(_parse_uploaded_file, _get_valid_matched_individuals)


SAMPLE_TYPE_MAP = [
    ('bam', IgvSample.SAMPLE_TYPE_ALIGNMENT),
    ('cram', IgvSample.SAMPLE_TYPE_ALIGNMENT),
    ('bigWig', IgvSample.SAMPLE_TYPE_COVERAGE),
    ('junctions.bed.gz', IgvSample.SAMPLE_TYPE_JUNCTION),
    ('bed.gz', IgvSample.SAMPLE_TYPE_GCNV),
]


@pm_or_data_manager_required
def update_individual_igv_sample(request, individual_guid):
    return update_individual_igv_sample_base(request, individual_guid)


def update_individual_igv_sample_base(request, individual_guid):
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)

    try:
        file_path = request_json.get('filePath')
        if not file_path:
            raise ValueError('request must contain fields: filePath')

        sample_type = next((st for suffix, st in SAMPLE_TYPE_MAP if file_path.endswith(suffix)), None)
        if not sample_type:
            raise Exception('Invalid file extension for "{}" - valid extensions are {}'.format(
                file_path, ', '.join([suffix for suffix, _ in SAMPLE_TYPE_MAP])))
        if not does_file_exist(file_path, user=request.user):
            raise Exception('Error accessing "{}"'.format(file_path))

        sample, created = get_or_create_model_from_json(
            IgvSample, create_json={'individual': individual, 'sample_type': sample_type},
            update_json={'file_path': file_path, 'sample_id': request_json.get('sampleId')}, user=request.user)

        response = {
            'igvSamplesByGuid': {
                sample.guid: get_json_for_sample(sample, individual_guid=individual_guid, family_guid=individual.family.guid, project_guid=project.guid)}
        }
        if created:
            response['individualsByGuid'] = {
                individual.guid: {'igvSampleGuids': [s.guid for s in individual.igvsample_set.all()]}
            }
        return create_json_response(response)
    except Exception as e:
        error = str(e)
        return create_json_response({'error': error}, status=400, reason=error)


@login_and_policies_required
def fetch_igv_track(request, project_guid, igv_track_path):

    get_project_and_check_permissions(project_guid, request.user)

    if igv_track_path.endswith('.bam.bai') and not does_file_exist(igv_track_path, user=request.user):
        igv_track_path = igv_track_path.replace('.bam.bai', '.bai')

    if is_google_bucket_file_path(igv_track_path):
        return _stream_gs(request, igv_track_path)

    return _stream_file(request, igv_track_path)


def _stream_gs(request, gs_path):
    headers = _get_gs_rest_api_headers(request.META.get('HTTP_RANGE'), gs_path, user=request.user)

    response = requests.get(
        f"{GS_STORAGE_URL}/{gs_path.replace('gs://', '', 1)}",
        headers=headers,
        stream=True)

    return StreamingHttpResponse(response.iter_content(chunk_size=65536), status=response.status_code,
                                 content_type='application/octet-stream')


def _get_gs_rest_api_headers(range_header, gs_path, user=None):
    headers = {'Authorization': 'Bearer {}'.format(_get_access_token(user))}
    if range_header:
        headers['Range'] = range_header
    google_project = get_google_project(gs_path)
    if google_project:
        headers['x-goog-user-project'] = get_google_project(gs_path)

    return headers


def _get_token_expiry(token):
    response = requests.post('https://www.googleapis.com/oauth2/v1/tokeninfo',
                             headers={'Content-Type': 'application/x-www-form-urlencoded'},
                             data='access_token={}'.format(token))
    if response.status_code == 200:
        result = json.loads(response.text)
        return result['expires_in']
    else:
        return 0


def _get_access_token(user):
    access_token = safe_redis_get_json(GS_STORAGE_ACCESS_CACHE_KEY)
    if not access_token:
        process = run_command('gcloud auth print-access-token', user=user)
        if process.wait() == 0:
            access_token = next(process.stdout).decode('utf-8').strip()
            expires_in = _get_token_expiry(access_token)
            safe_redis_set_json(GS_STORAGE_ACCESS_CACHE_KEY, access_token, expire=expires_in-5)
    return access_token


def _stream_file(request, path):
    # based on https://gist.github.com/dcwatson/cb5d8157a8fa5a4a046e
    content_type = 'application/octet-stream'
    range_header = request.META.get('HTTP_RANGE', None)
    if range_header:
        range_match = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I).match(range_header)
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte)
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(
            file_iter(path, byte_range=(first_byte, last_byte), raw_content=True, user=request.user), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s' % (first_byte, last_byte)
    else:
        resp = StreamingHttpResponse(file_iter(path, raw_content=True, user=request.user), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    return resp


def igv_genomes_proxy(request, cloud_host, file_path):
    # IGV does not properly set CORS header and cannot directly access the genomes resource from the browser without
    # using this server-side proxy
    headers = {}
    range_header = request.META.get('HTTP_RANGE')
    if range_header:
        headers['Range'] = range_header

    genome_response = requests.get(f'{CLOUD_STORAGE_URLS[cloud_host]}/{file_path}', headers=headers)
    proxy_response = HttpResponse(
        content=genome_response.content,
        status=genome_response.status_code,
    )
    return proxy_response


@service_account_access
def sa_get_igv_updates_required(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    json_body = json.loads(request.body)
    json_records = json_body.get('mapping')

    def _get_valid_matched_individuals(individual_dataset_mapping):
        matched_individuals = Individual.objects.filter(
            family__project=project, individual_id__in=individual_dataset_mapping.keys()
        )
        unmatched_individuals = set(individual_dataset_mapping.keys()) - {i.individual_id for i in matched_individuals}
        if len(unmatched_individuals) > 0:
            raise Exception('The following Individual IDs do not exist: {}'.format(", ".join(unmatched_individuals)))

        return {i: individual_dataset_mapping[i.individual_id] for i in matched_individuals}

    info, all_updates = _post_process_igv_records(
        individual_dataset_mapping=json_records,
        get_valid_matched_individuals=_get_valid_matched_individuals,
        filename='<body>'
    )

    # I was initially looking to completely merge this in, except the call is slow
    # and I genuinely think the request will time out, so make the caller do the
    # spacing out.
    return create_json_response({
        'updates': all_updates,
        'errors': [],
        'info': info,
    })

@service_account_access
def sa_update_igv_individual(request, individual_guid):
    return update_individual_igv_sample_base(request, individual_guid)

# @service_account_access
# def sa_update_igv_bulk(request, individual_guid):
#     return update_individual_igv_sample_base(request, individual_guid)