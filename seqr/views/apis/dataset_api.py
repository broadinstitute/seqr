import datetime
import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Dataset, ElasticsearchDataset, CAN_EDIT, Project
from seqr.utils.file_utils import get_file_stats
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_dataset
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
                'name':  <project name>,
                'description': <project description>,
            }
        }

        Response body - will contain the following structure, representing the updated project:
            {
                'projectsByGuid':  {
                    <projectGuid1> : { ... <project key-value pairs> ... }
                }
            }

    """

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)

    request_json = json.loads(request.body)
    if 'form' not in request_json:
        return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")

    form_data = request_json['form']

    logger.info("add_dataset_handler", form_data)

    return create_json_response({
        'errors': ['this is it'],
        'projectsByGuid': {
            project.guid: None #_get_json_for_dataset(dataset, request.user)
        },
    })


def get_dataset_by_id(dataset_id):
    try:
        return Dataset.objects.get(dataset_id=dataset_id)
    except ObjectDoesNotExist:
        return None


def get_dataset(project, analysis_type, source_file_path):
    try:
        return Dataset.objects.get(
            analysis_type=analysis_type,
            source_file_path=source_file_path,
            project=project,
        )
    except ObjectDoesNotExist:
        return None


def get_or_create_dataset(project, analysis_type, source_file_path, dataset_id=None):

    try:
        if dataset_id is None:
            dataset = Dataset.objects.get(
                analysis_type=analysis_type,
                source_file_path=source_file_path,
                project=project,
            )
        else:
            dataset = Dataset.objects.get(
                dataset_id=dataset_id,
            )

            dataset.analysis_type = analysis_type
            dataset.source_file_path = source_file_path
            dataset.project = project
            dataset.save()

    except ObjectDoesNotExist:
        logger.info("Creating %s dataset for %s" % (analysis_type, source_file_path))
        dataset = create_dataset(project, analysis_type, source_file_path, dataset_id=dataset_id)

    return dataset


def create_dataset(project, analysis_type, source_file_path, is_loaded=False, loaded_date=None, dataset_id=None):

    # compute a dataset_id based on source_file_path
    if dataset_id is None:
        file_stats = get_file_stats(source_file_path)
        dataset_id = "_".join(map(str, [
            datetime.datetime.fromtimestamp(float(file_stats.ctime)).strftime('%Y%m%d'),
            os.path.basename(source_file_path).split(".")[0][:20],
            file_stats.size
        ]))

    # create the Dataset
    dataset = Dataset.objects.create(
        dataset_id=dataset_id,
        analysis_type=analysis_type,
        source_file_path=source_file_path,
        project=project,
        is_loaded=is_loaded,
        loaded_date=loaded_date,
    )

    return dataset


def get_or_create_elasticsearch_dataset(
        project,
        analysis_type,
        genome_version,
        source_file_path,
        elasticsearch_host=None,
        elasticsearch_index=None,
        is_loaded=False,
        loaded_date=None,
):

    try:
        if elasticsearch_index is None:
            dataset = ElasticsearchDataset.objects.get(
                project=project,
                analysis_type=analysis_type,
                genome_version=genome_version,
                source_file_path=source_file_path,
                dataset_location=elasticsearch_host,
                dataset_id=elasticsearch_index,
            )
        else:
            dataset = ElasticsearchDataset.objects.get(
                dataset_id=elasticsearch_index,
            )

            dataset.project = project
            dataset.analysis_type = analysis_type
            dataset.source_file_path = source_file_path
            if elasticsearch_host is not None:
                dataset.dataset_location = elasticsearch_host
            if elasticsearch_index is not None:
                dataset.dataset_id = elasticsearch_index
            if is_loaded is not None:
                dataset.is_loaded = is_loaded
            if loaded_date is not None:
                dataset.loaded_date = loaded_date
            dataset.save()

    except ObjectDoesNotExist:
        logger.info("Creating %s dataset for %s" % (analysis_type, source_file_path))
        dataset = create_elasticsearch_dataset(
            project,
            analysis_type,
            source_file_path,
            elasticsearch_host=elasticsearch_host,
            elasticsearch_index=elasticsearch_index,
            is_loaded=is_loaded,
            loaded_date=loaded_date,
        )

    return dataset


def create_elasticsearch_dataset(
        project,
        analysis_type,
        source_file_path,
        elasticsearch_host=None,
        elasticsearch_index=None,
        is_loaded=False,
        loaded_date=None,
):

    # compute a dataset_id based on source_file_path
    if elasticsearch_index is None:
        raise ValueError("elasticsearch_index is None")
    
        #file_stats = get_file_stats(source_file_path)
        #dataset_id = "_".join(map(str, [
        #     datetime.datetime.fromtimestamp(float(file_stats.ctime)).strftime('%Y%m%d'),
        #    os.path.basename(source_file_path).split(".")[0][:20],
        #    file_stats.size
        #]))

    # create the Dataset
    dataset = ElasticsearchDataset.objects.create(
        analysis_type=analysis_type,
        source_file_path=source_file_path,
        project=project,
        dataset_location=elasticsearch_host,
        dataset_id=elasticsearch_index,
        is_loaded=is_loaded,
        loaded_date=loaded_date,
    )

    return dataset


def link_dataset_to_sample_records(dataset, sample_records):
    for sample in sample_records:
        dataset.samples.add(sample)


