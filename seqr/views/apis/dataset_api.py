import json
import logging
from pprint import pformat

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Individual, CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.dataset_utils import add_dataset
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def add_dataset_handler(request, project_guid):
    """Update project metadata - including one or more of these fields: name, description

    Args:
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'form' : {
                'sampleType':  <"WGS", "WES", or "RNA">
                'datasetType': <"VARIANTS", or "ALIGN">
                'genomeVersion': <"GRCH37", or "GRCH38">
            }
        }

        Response body - will contain the following structure:

    """

    logger.info("add_dataset_handler: " + str(request))

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)

    request_json = json.loads(request.body)

    logger.info("add_dataset_handler: received %s" % pformat(request_json))

    required_fields = ['sampleType', 'datasetType', 'elasticsearchIndex']
    if any(field not in request_json for field in required_fields):
        raise ValueError(
            "request must contain fields: {}".format(', '.join(required_fields)))

    sample_type = request_json['sampleType']
    dataset_type = request_json['datasetType']
    elasticsearch_index = request_json['elasticsearchIndex']
    dataset_path = request_json.get('datasetPath')
    dataset_name = request_json.get('datasetName')

    ignore_extra_samples_in_callset = request_json.get('ignoreExtraSamplesInCallset')
    sample_ids_to_individual_ids_file_id = request_json.get('sampleIdsToIndividualIds', {}).get('uploadedFileId')

    try:
        updated_samples, created_sample_ids = add_dataset(
            project=project,
            elasticsearch_index=elasticsearch_index,
            sample_type=sample_type,
            dataset_type=dataset_type,
            dataset_path=dataset_path,
            dataset_name=dataset_name,
            max_edit_distance=0,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
            sample_ids_to_individual_ids_file_id=sample_ids_to_individual_ids_file_id,
        )
        updated_sample_json = get_json_for_samples(updated_samples, project_guid=project_guid)
        response = {
            'samplesByGuid': {s['sampleGuid']: s for s in updated_sample_json}
        }
        updated_individuals = {s['individualGuid'] for s in updated_sample_json if s['sampleId'] in created_sample_ids}
        if updated_individuals:
            individuals = Individual.objects.filter(guid__in=updated_individuals).prefetch_related('sample_set').only('guid')
            response['individualsByGuid'] = {
                ind.guid: {'sampleGuids': [s.guid for s in ind.sample_set.only('guid').all()]} for ind in individuals
            }
        return create_json_response(response)
    except Exception as e:
        return create_json_response({'errors': [e.message or str(e)]}, status=400)
