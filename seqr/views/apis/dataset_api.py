import json

from seqr.utils.search.add_data_utils import basic_notify_search_data_loaded
from seqr.utils.search.elasticsearch.es_utils import validate_es_index_metadata_and_get_samples
from seqr.utils.search.utils import es_only
from seqr.models import Individual, Family, Sample
from seqr.views.utils.dataset_utils import match_and_update_search_samples, load_mapping_file
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, data_manager_required


@data_manager_required
@es_only
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
        inactivated_sample_guids, updated_family_guids, updated_samples = _add_new_es_search_samples(
            request_json, project, request.user, notify=True)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    response_json = _get_samples_json(updated_samples, inactivated_sample_guids, project_guid)
    response_json['familiesByGuid'] = {family_guid: {'analysisStatus': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}
                                       for family_guid in updated_family_guids}

    return create_json_response(response_json)


def _add_new_es_search_samples(request_json, project, user, notify=False, expected_families=None):
    dataset_type = request_json.get('datasetType')
    if dataset_type not in Sample.DATASET_TYPE_LOOKUP:
        raise ValueError(f'Invalid dataset type "{dataset_type}"')

    sample_ids, sample_type, sample_data = validate_es_index_metadata_and_get_samples(request_json, project)
    if not sample_ids:
        raise ValueError('No samples found. Make sure the specified caller type is correct')

    sample_id_to_individual_id_mapping = load_mapping_file(
        request_json['mappingFilePath'], user) if request_json.get('mappingFilePath') else {}
    ignore_extra_samples = request_json.get('ignoreExtraSamplesInCallset')
    sample_project_tuples = [(sample_id, project.name) for sample_id in sample_ids]
    new_samples, updated_samples, inactivated_sample_guids, updated_family_guids = match_and_update_search_samples(
        projects=[project],
        user=user,
        sample_project_tuples=sample_project_tuples,
        sample_data=sample_data,
        sample_type=sample_type,
        dataset_type=dataset_type,
        expected_families=expected_families,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_unmatched_error_template=None if ignore_extra_samples else 'Matches not found for sample ids: {sample_ids}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'
    )

    if notify:
        basic_notify_search_data_loaded(project, dataset_type, sample_type, new_samples.values_list('sample_id', flat=True))

    return inactivated_sample_guids, updated_family_guids, updated_samples


def _get_samples_json(updated_samples, inactivated_sample_guids, project_guid):
    updated_sample_json = get_json_for_samples(updated_samples, project_guid=project_guid)
    sample_response = {sample_guid: {'isActive': False} for sample_guid in inactivated_sample_guids}
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
