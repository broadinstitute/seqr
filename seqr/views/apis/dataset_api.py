import json
import logging
from pprint import pformat

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import CAN_EDIT, Sample
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.dataset_utils import add_variant_calls_dataset, add_read_alignment_dataset
from seqr.views.utils.json_utils import create_json_response
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

    ignore_extra_samples_in_callset = request_json.get('ignoreExtraSamplesInCallset')
    sample_ids_to_individual_ids_path = request_json.get('sampleIdsToIndividualIdsPath')

    if sample_ids_to_individual_ids_path:
        return create_json_response({
            'errors': ["Sample ids to individual ids mapping - not yet supported"],
        }, status=400)

    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        errors, info = add_variant_calls_dataset(
            project=project,
            elasticsearch_index=elasticsearch_index,
            sample_type=sample_type,
            dataset_path=dataset_path,
            max_edit_distance=0,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
            sample_ids_to_individual_ids_path=sample_ids_to_individual_ids_path,
        )
    elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
        # TODO
        errors, info = add_read_alignment_dataset(
            project,
            sample_type,
            dataset_path,
            max_edit_distance=0,
            elasticsearch_index=elasticsearch_index,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
        )
    else:
        errors = ["Dataset type not supported: {}".format(dataset_type)]

    if errors:
        return create_json_response({'errors': errors}, status=400)

    return create_json_response({'info': info})
