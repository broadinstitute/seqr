import json
import logging
import traceback
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from seqr.models import Individual, CAN_EDIT, Sample
from seqr.model_utils import update_xbrowse_vcfffiles, find_matching_xbrowse_model
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.dataset_utils import match_sample_ids_to_sample_records, validate_index_metadata, \
    get_elasticsearch_index_samples, load_mapping_file, load_uploaded_mapping_file, validate_alignment_dataset_path
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_project_from_json, update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.views.utils.variant_utils import reset_cached_search_results


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    request_json = json.loads(request.body)

    try:
        if 'elasticsearchIndex' not in request_json:
            raise ValueError('"elasticsearchIndex" is required')
        elasticsearch_index = request_json['elasticsearchIndex'].strip()

        sample_ids, index_metadata = get_elasticsearch_index_samples(elasticsearch_index)
        validate_index_metadata(index_metadata, project, elasticsearch_index)
        sample_type = index_metadata['sampleType']
        dataset_path = index_metadata['sourceFilePath']

        sample_id_to_individual_id_mapping = load_mapping_file(
            request_json['mappingFilePath']) if request_json.get('mappingFilePath') else {}

        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project=project,
            sample_ids=sample_ids,
            sample_type=sample_type,
            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            elasticsearch_index=elasticsearch_index,
            sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
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

        included_family_individuals = defaultdict(set)
        for sample in matched_sample_id_to_sample_record.values():
            included_family_individuals[sample.individual.family].add(sample.individual.individual_id)
        missing_family_individuals = []
        for family, individual_ids in included_family_individuals.items():
            missing_indivs = family.individual_set.filter(
                sample__sample_status=Sample.SAMPLE_STATUS_LOADED,
                sample__dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS
            ).exclude(individual_id__in=individual_ids)
            if missing_indivs:
                missing_family_individuals.append(
                    '{} ({})'.format(family.family_id, ', '.join([i.individual_id for i in missing_indivs]))
                )
        if missing_family_individuals:
            raise Exception(
                'The following families are included in the callset but are missing some family members: {}.'.format(
                    ', '.join(missing_family_individuals)
                ))

        _update_samples(
            matched_sample_id_to_sample_record, elasticsearch_index=elasticsearch_index, dataset_path=dataset_path
        )

    except Exception as e:
        traceback.print_exc()
        return create_json_response({'errors': [e.message or str(e)]}, status=400)

    if not matched_sample_id_to_sample_record:
        return create_json_response({'samplesByGuid': {}})

    update_project_from_json(project, {'has_new_search': True})
    reset_cached_search_results(project)

    update_xbrowse_vcfffiles(
        project, sample_type, elasticsearch_index, dataset_path, matched_sample_id_to_sample_record
    )

    return create_json_response(_get_samples_json(matched_sample_id_to_sample_record, project_guid))


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def add_alignment_dataset_handler(request, project_guid):
    """Create or update samples for the given dataset

    Args:
        request: Django request object
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'sampleType':  <"WGS", "WES", or "RNA"> (required)
            'datasetType': <"VARIANTS", or "ALIGN"> (required)
            'elasticsearchIndex': <String>
            'datasetPath': <String>
            'datasetName': <String>
            'ignoreExtraSamplesInCallset': <Boolean>
            'mappingFile': { 'uploadedFileId': <Id for temporary uploaded file> }
        }

        Response body - will contain the following structure:

    """
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    request_json = json.loads(request.body)

    try:
        required_fields = ['sampleType', 'mappingFile']
        if any(field not in request_json for field in required_fields):
            raise ValueError(
                "request must contain fields: {}".format(', '.join(required_fields)))

        sample_type = request_json['sampleType']
        if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
            raise Exception("Sample type not supported: {}".format(sample_type))
        mapping_file_id = request_json['mappingFile']['uploadedFileId']

        sample_id_to_individual_id_mapping = {}
        sample_dataset_path_mapping = {}
        for individual_id, dataset_path in load_uploaded_mapping_file(mapping_file_id).items():
            if not (dataset_path.endswith(".bam") or dataset_path.endswith(".cram")):
                raise Exception('BAM / CRAM file "{}" must have a .bam or .cram extension'.format(dataset_path))
            validate_alignment_dataset_path(dataset_path)
            sample_id = dataset_path.split('/')[-1].split('.')[0]
            sample_id_to_individual_id_mapping[sample_id] = individual_id
            sample_dataset_path_mapping[sample_id] = dataset_path

        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project=project,
            sample_ids=sample_id_to_individual_id_mapping.keys(),
            sample_type=sample_type,
            dataset_type=Sample.DATASET_TYPE_READ_ALIGNMENTS,
            sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        )

        unmatched_samples = set(sample_id_to_individual_id_mapping.keys()) - set(matched_sample_id_to_sample_record.keys())
        if len(unmatched_samples) > 0:
            raise Exception('The following Individual IDs do not exist: {}'.format(", ".join(unmatched_samples)))

        _update_samples(matched_sample_id_to_sample_record, sample_dataset_path_mapping=sample_dataset_path_mapping)

    except Exception as e:
        traceback.print_exc()
        return create_json_response({'errors': [e.message or str(e)]}, status=400)

    if not matched_sample_id_to_sample_record:
        return create_json_response({'samplesByGuid': {}})

    # Deprecated update VCFFile records
    for sample in matched_sample_id_to_sample_record.values():
        base_indiv = find_matching_xbrowse_model(sample.individual)
        if base_indiv:
            base_indiv.bam_file_path = sample.dataset_file_path
            base_indiv.save()

    return create_json_response(_get_samples_json(matched_sample_id_to_sample_record, project_guid))


def _update_samples(matched_sample_id_to_sample_record, elasticsearch_index=None, dataset_path=None, sample_dataset_path_mapping=None):
    loaded_date = timezone.now()
    for sample_id, sample in matched_sample_id_to_sample_record.items():
        sample_update_json = {
            'dataset_file_path': dataset_path or sample_dataset_path_mapping[sample_id],
        }
        if elasticsearch_index:
            sample_update_json['elasticsearch_index'] = elasticsearch_index
        if sample.sample_status != Sample.SAMPLE_STATUS_LOADED:
            sample_update_json['sample_status'] = Sample.SAMPLE_STATUS_LOADED
            sample_update_json['loaded_date'] = loaded_date
        update_model_from_json(sample, sample_update_json)


def _get_samples_json(matched_sample_id_to_sample_record, project_guid):
    updated_sample_json = get_json_for_samples(matched_sample_id_to_sample_record.values(), project_guid=project_guid)
    response = {
        'samplesByGuid': {s['sampleGuid']: s for s in updated_sample_json}
    }
    updated_individuals = {s['individualGuid'] for s in updated_sample_json}
    if updated_individuals:
        individuals = Individual.objects.filter(guid__in=updated_individuals).prefetch_related('sample_set',
                                                                                               'family').only('guid')
        response['individualsByGuid'] = {
            ind.guid: {'sampleGuids': [s.guid for s in ind.sample_set.only('guid').all()]} for ind in individuals
        }
    return response
