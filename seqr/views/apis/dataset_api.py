import json

from seqr.utils.search.add_data_utils import add_new_es_search_samples
from seqr.models import Individual, Family
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, data_manager_required


@data_manager_required
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
        inactivated_sample_guids, updated_family_guids, updated_samples = add_new_es_search_samples(
            request_json, project, request.user, notify=True)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    response_json = _get_samples_json(updated_samples, inactivated_sample_guids, project_guid)
    response_json['familiesByGuid'] = {family_guid: {'analysisStatus': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}
                                       for family_guid in updated_family_guids}

    return create_json_response(response_json)


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
