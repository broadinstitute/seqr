from collections import defaultdict
import json
import re
from django.http import StreamingHttpResponse

from seqr.models import Individual, IgvSample
from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.views.utils.file_utils import save_uploaded_file
from seqr.views.utils.json_to_orm_utils import get_or_create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import  get_json_for_sample
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    login_and_policies_required, pm_or_data_manager_required

import logging
logger = logging.getLogger(__name__)


@pm_or_data_manager_required
def receive_igv_table_handler(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    info = []

    def _process_alignment_records(rows, **kwargs):
        invalid_row = next((row for row in rows if not 2 <= len(row) <= 3), None)
        if invalid_row:
            raise ValueError("Must contain 2 or 3 columns: " + ', '.join(invalid_row))
        parsed_records = defaultdict(list)
        for row in rows:
            parsed_records[row[0]].append({'filePath': row[1], 'sampleId': row[2] if len(row)> 2 else None})
        return parsed_records

    try:
        uploaded_file_id, filename, individual_dataset_mapping = save_uploaded_file(request, process_records=_process_alignment_records)

        matched_individuals = Individual.objects.filter(family__project=project, individual_id__in=individual_dataset_mapping.keys())
        unmatched_individuals = set(individual_dataset_mapping.keys()) - {i.individual_id for i in matched_individuals}
        if len(unmatched_individuals) > 0:
            raise Exception('The following Individual IDs do not exist: {}'.format(", ".join(unmatched_individuals)))

        info.append('Parsed {} rows in {} individuals from {}'.format(
            sum([len(rows) for rows in individual_dataset_mapping.values()]), len(individual_dataset_mapping), filename))

        existing_sample_files = defaultdict(set)
        for sample in IgvSample.objects.select_related('individual').filter(individual__in=matched_individuals):
            existing_sample_files[sample.individual.individual_id].add(sample.file_path)

        unchanged_rows = set()
        for individual_id, updates in individual_dataset_mapping.items():
            unchanged_rows.update([
                (individual_id, update['filePath']) for update in updates
                if update['filePath'] in existing_sample_files[individual_id]
            ])

        if unchanged_rows:
            info.append('No change detected for {} rows'.format(len(unchanged_rows)))

        all_updates = []
        for i in matched_individuals:
            all_updates += [
                dict(individualGuid=i.guid, **update) for update in individual_dataset_mapping[i.individual_id]
                if (i.individual_id, update['filePath']) not in unchanged_rows
            ]

    except Exception as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    response = {
        'updates': all_updates,
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'info': info,
    }
    return create_json_response(response)


SAMPLE_TYPE_MAP = {
    'bam': IgvSample.SAMPLE_TYPE_ALIGNMENT,
    'cram': IgvSample.SAMPLE_TYPE_ALIGNMENT,
    'bigWig': IgvSample.SAMPLE_TYPE_COVERAGE,
    'junctions.bed.gz': IgvSample.SAMPLE_TYPE_JUNCTION,
    'dcr.bed.gz': IgvSample.SAMPLE_TYPE_GCNV,
}

@pm_or_data_manager_required
def update_individual_igv_sample(request, individual_guid):
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)

    try:
        file_path = request_json.get('filePath')
        if not file_path:
            raise ValueError('request must contain fields: filePath')

        sample_type = next((st for suffix, st in SAMPLE_TYPE_MAP.items() if file_path.endswith(suffix)), None)
        if not sample_type:
            raise Exception('Invalid file extension for "{}" - valid extensions are {}'.format(
                file_path, ', '.join(SAMPLE_TYPE_MAP.keys())))
        if not does_file_exist(file_path):
            raise Exception('Error accessing "{}"'.format(file_path))

        sample, created = get_or_create_model_from_json(
            IgvSample, create_json={'individual': individual, 'sample_type': sample_type},
            update_json={'file_path': file_path, 'sample_id': request_json.get('sampleId')}, user=request.user)

        response = {
            'igvSamplesByGuid': {
                sample.guid: get_json_for_sample(sample, individual_guid=individual_guid, project_guid=project.guid)}
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

    if igv_track_path.endswith('.bam.bai') and not does_file_exist(igv_track_path):
        igv_track_path = igv_track_path.replace('.bam.bai', '.bai')

    return _stream_file(request, igv_track_path)


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
            file_iter(path, byte_range=(first_byte, last_byte), raw_content=True), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s' % (first_byte, last_byte)
    else:
        resp = StreamingHttpResponse(file_iter(path, raw_content=True), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    return resp
