import json
import logging
from pprint import pformat

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.dataset.dataset_validation import validate_dataset
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
    if 'form' not in request_json:
        return create_json_response(
            {}, status=400, reason="Invalid request: 'form' not in request_json")

    form_data = request_json['form']

    logger.info("add_dataset_handler: received %s" % pformat(form_data))

    if "sampleType" not in form_data or \
            "datasetType" not in form_data or \
            "genomeVersion" not in form_data or \
            "datasetPath" not in form_data:
        raise ValueError(
            "request must contain fields: sampleType, datasetType, genomeVersion, datasetPath")

    name = form_data.get('name')
    description = form_data.get('description')
    sample_type = form_data.get('sampleType')
    dataset_type = form_data.get('datasetType')
    genome_version = form_data.get('genomeVersion')
    dataset_path = form_data.get('datasetPath')

    errors, warnings, info = validate_dataset(
        project,
        sample_type,
        dataset_type,
        genome_version,
        dataset_path,
        max_edit_distance=0,
        dataset_id=None)

    # {sampleType: "WGS", datasetType: "BAMS", genomeVersion: "GRCH37", datasetPath: "gs://dataset/"}

    if errors:
        return create_json_response({
            'errors': errors,
            'warnings': warnings,
            'info': info,
        })

    return create_json_response({
        'errors': errors,
        'warnings': warnings,
        'info': info,
        'status': 'done',
    })



