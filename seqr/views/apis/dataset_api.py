import json
import logging
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import prefetch_related_objects
from django.utils import timezone

from seqr.models import Individual, Sample, Family, IgvSample
from seqr.views.utils.dataset_utils import match_sample_ids_to_sample_records, validate_index_metadata, \
    get_elasticsearch_index_samples, load_mapping_file, validate_alignment_dataset_path
from seqr.views.utils.file_utils import save_uploaded_file
from seqr.views.utils.json_to_orm_utils import get_or_create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples, get_json_for_sample
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def add_variants_dataset_handler(request, project_guid):
    """Create or update samples for the given variant dataset

    Args:
        request: Django request object
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'elasticsearchIndex': <String> (required)
            'ignoreExtraSamplesInCallset': <Boolean>
            'mappingFilePath':  <String>
        }

        Response body - will contain the following structure:

    """

    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    request_json = json.loads(request.body)

    try:
        required_fields = ['elasticsearchIndex', 'datasetType']
        if any(field not in request_json for field in required_fields):
            raise ValueError('request must contain fields: {}'.format(', '.join(required_fields)))
        elasticsearch_index = request_json['elasticsearchIndex'].strip()
        dataset_type = request_json['datasetType']
        if dataset_type not in Sample.DATASET_TYPE_LOOKUP:
            raise ValueError('Invalid dataset type "{}"'.format(dataset_type))

        sample_ids, index_metadata = get_elasticsearch_index_samples(elasticsearch_index, dataset_type=dataset_type)
        if not sample_ids:
            raise ValueError('No samples found in the index. Make sure the specified caller type is correct')
        validate_index_metadata(index_metadata, project, elasticsearch_index, dataset_type=dataset_type)
        sample_type = index_metadata['sampleType']

        sample_id_to_individual_id_mapping = load_mapping_file(
            request_json['mappingFilePath']) if request_json.get('mappingFilePath') else {}

        loaded_date = timezone.now()
        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project=project,
            user=request.user,
            sample_ids=sample_ids,
            sample_type=sample_type,
            dataset_type=dataset_type,
            elasticsearch_index=elasticsearch_index,
            sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
            loaded_date=loaded_date,
        )

        unmatched_samples = set(sample_ids) - set(matched_sample_id_to_sample_record.keys())

        if request_json.get('ignoreExtraSamplesInCallset'):
            if len(matched_sample_id_to_sample_record) == 0:
                raise Exception(
                    "None of the individuals or samples in the project matched the {} expected sample id(s)".format(
                        len(sample_ids)
                    ))
        elif len(unmatched_samples) > 0:
            raise Exception(
                'Matches not found for ES sample ids: {}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'.format(
                    ", ".join(unmatched_samples)))

        prefetch_related_objects(list(matched_sample_id_to_sample_record.values()), 'individual__family')
        included_families = {sample.individual.family for sample in matched_sample_id_to_sample_record.values()}

        missing_individuals = Individual.objects.filter(
            family__in=included_families,
            sample__is_active=True,
            sample__dataset_type=dataset_type,
        ).exclude(sample__in=matched_sample_id_to_sample_record.values()).select_related('family')
        missing_family_individuals = defaultdict(list)
        for individual in missing_individuals:
            missing_family_individuals[individual.family].append(individual)

        if missing_family_individuals:
            raise Exception(
                'The following families are included in the callset but are missing some family members: {}.'.format(
                    ', '.join(sorted(
                        ['{} ({})'.format(family.family_id, ', '.join(sorted([i.individual_id for i in missing_indivs])))
                         for family, missing_indivs in missing_family_individuals.items()]
                    ))))

        inactivate_sample_guids = _update_variant_samples(
            matched_sample_id_to_sample_record, request.user, elasticsearch_index, loaded_date, dataset_type)

    except Exception as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    family_guids_to_update = [
        family.guid for family in included_families if family.analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        request.user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    response_json = _get_samples_json(matched_sample_id_to_sample_record, inactivate_sample_guids, project_guid)
    response_json['familiesByGuid'] = {family_guid: {'analysisStatus': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}
                                       for family_guid in family_guids_to_update}

    return create_json_response(response_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def receive_igv_table_handler(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    info = []

    def _process_alignment_records(rows, **kwargs):
        invalid_row = next((row for row in rows if len(row) != 2), None)
        if invalid_row:
            raise ValueError("Must contain 2 columns: " + ', '.join(invalid_row))
        return {row[0]: row[1] for row in rows}

    try:
        uploaded_file_id, filename, individual_dataset_mapping = save_uploaded_file(request, process_records=_process_alignment_records)

        matched_individuals = Individual.objects.filter(family__project=project, individual_id__in=individual_dataset_mapping.keys())
        unmatched_individuals = set(individual_dataset_mapping.keys()) - {i.individual_id for i in matched_individuals}
        if len(unmatched_individuals) > 0:
            raise Exception('The following Individual IDs do not exist: {}'.format(", ".join(unmatched_individuals)))

        info.append('Parsed {} rows from {}'.format(len(individual_dataset_mapping), filename))

        existing_samples = IgvSample.objects.select_related('individual').filter(individual__in=matched_individuals)
        unchanged_individual_ids = {s.individual.individual_id for s in existing_samples
                                    if individual_dataset_mapping[s.individual.individual_id] == s.file_path}
        if unchanged_individual_ids:
            info.append('No change detected for {} individuals'.format(len(unchanged_individual_ids)))

        updates_by_individual_guid = {i.guid: individual_dataset_mapping[i.individual_id] for i in matched_individuals
                                      if i.individual_id not in unchanged_individual_ids}

    except Exception as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    response = {
        'updatesByIndividualGuid': updates_by_individual_guid,
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'info': info,
    }
    return create_json_response(response)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_individual_igv_sample(request, individual_guid):
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)

    try:
        required_fields = ['filePath']
        if any(field not in request_json for field in required_fields):
            raise ValueError(
                "request must contain fields: {}".format(', '.join(required_fields)))

        file_path = request_json['filePath']
        if not (file_path.endswith(".bam") or file_path.endswith(".cram")):
            raise Exception('BAM / CRAM file "{}" must have a .bam or .cram extension'.format(file_path))
        validate_alignment_dataset_path(file_path)

        sample, created = get_or_create_model_from_json(
            IgvSample, create_json={'individual': individual}, update_json={'file_path': file_path}, user=request.user)

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


def _update_variant_samples(matched_sample_id_to_sample_record, user, elasticsearch_index, loaded_date=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    if not loaded_date:
        loaded_date = timezone.now()
    updated_samples = [sample.id for sample in matched_sample_id_to_sample_record.values()]

    activated_sample_guids = Sample.bulk_update(user, {
        'elasticsearch_index': elasticsearch_index,
        'is_active': True,
        'loaded_date': loaded_date,
    }, id__in=updated_samples, is_active=False)

    matched_sample_id_to_sample_record.update({
        sample.sample_id: sample for sample in Sample.objects.filter(guid__in=activated_sample_guids)
    })

    inactivate_samples = Sample.objects.filter(
        individual_id__in={sample.individual_id for sample in matched_sample_id_to_sample_record.values()},
        is_active=True,
        dataset_type=dataset_type,
    ).exclude(id__in=updated_samples)

    inactivate_sample_guids = Sample.bulk_update(user, {'is_active': False}, queryset=inactivate_samples)

    return inactivate_sample_guids


def _get_samples_json(matched_sample_id_to_sample_record, inactivate_sample_guids, project_guid):
    updated_sample_json = get_json_for_samples(list(matched_sample_id_to_sample_record.values()), project_guid=project_guid)
    sample_response = {sample_guid: {'isActive': False} for sample_guid in inactivate_sample_guids}
    sample_response.update({s['sampleGuid']: s for s in updated_sample_json})
    response = {
        'samplesByGuid': sample_response
    }
    updated_individuals = {s['individualGuid'] for s in updated_sample_json}
    if updated_individuals:
        individuals = Individual.objects.filter(guid__in=updated_individuals).prefetch_related('sample_set')
        response['individualsByGuid'] = {
            ind.guid: {'sampleGuids': [s.guid for s in ind.sample_set.all()]} for ind in individuals
        }
    return response
