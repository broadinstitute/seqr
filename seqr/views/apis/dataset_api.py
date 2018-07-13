import json
import logging
from pprint import pformat

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Individual, CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.dataset_utils import add_dataset
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions

from xbrowse_server.base.models import VCFFile, Project as BaseProject

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def add_dataset_handler(request, project_guid):
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

    logger.info("add_dataset_handler: " + str(request))

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)

    request_json = json.loads(request.body)

    logger.info("add_dataset_handler: received %s" % pformat(request_json))

    required_fields = ['sampleType', 'datasetType']
    if any(field not in request_json for field in required_fields):
        raise ValueError(
            "request must contain fields: {}".format(', '.join(required_fields)))

    sample_type = request_json['sampleType']
    dataset_type = request_json['datasetType']
    elasticsearch_index = request_json.get('elasticsearchIndex')
    dataset_path = request_json.get('datasetPath')
    dataset_name = request_json.get('datasetName')

    ignore_extra_samples_in_callset = request_json.get('ignoreExtraSamplesInCallset')
    mapping_file_id = request_json.get('mappingFile', {}).get('uploadedFileId')

    try:
        updated_samples, created_sample_ids = add_dataset(
            project=project,
            sample_type=sample_type,
            dataset_type=dataset_type,
            elasticsearch_index=elasticsearch_index,
            dataset_path=dataset_path,
            dataset_name=dataset_name,
            max_edit_distance=0,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
            mapping_file_id=mapping_file_id,
        )

        # update VCFFile records
        if updated_samples:
            base_project = BaseProject.objects.get(seqr_project=project)
            vcf_file, created = VCFFile.objects.get_or_create(
                project=base_project,
                dataset_path=dataset_path,
                dataset_type=dataset_type,
                sample_type=sample_type,
                elasticsearch_index=elasticsearch_index,
                loaded_date=iter(updated_samples).next().loaded_date,
            )
            if created:
                logger.info("Created vcf file: " + str(vcf_file.__dict__))

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
