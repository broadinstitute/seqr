"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import settings
from seqr.model_utils import get_or_create_seqr_model, delete_seqr_model
from seqr.models import Project, Family, Individual, Sample, _slugify, CAN_EDIT, IS_OWNER
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.phenotips_api import create_phenotips_user, _get_phenotips_uname_and_pwd_for_project
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_project_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_project_handler(request):
    """Create a new project.

    HTTP POST
        Request body - should contain json params:
            name: Project name
            description: Project description

        Response body - will be json with the following structure, representing the ,created project:
            {
                'projectsByGuid':  { <projectGuid1> : { ... <project key-value pairs> ... } }
            }

    """
    request_json = json.loads(request.body)

    name = request_json.get('name')
    if not name:
        return create_json_response({}, status=400, reason="'Name' cannot be blank")

    description = request_json.get('description', '')
    genome_version = request_json.get('genomeVersion')

    #if not created:
    #    return create_json_response({}, status=400, reason="A project named '%(name)s' already exists" % locals())

    project = create_project(name, description=description, genome_version=genome_version, user=request.user)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_handler(request, project_guid):
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

    project = Project.objects.get(guid=project_guid)

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    update_project_from_json(project, request_json, allow_unknown_keys=True)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_handler(request, project_guid):
    """Delete project - request handler.

    Args:
        project_guid (string): GUID of the project to delete
    """

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=IS_OWNER)

    delete_project(project)

    return create_json_response({
        'projectsByGuid': {
            project.guid: None
        },
    })


def create_project(name, description=None, genome_version=None, user=None):
    """Creates a new project.

    Args:
        name (string): Project name
        description (string): optional description
        user (object): Django user that is creating this project
    """
    if not name:
        raise ValueError("Name not specified: %s" % (name,))

    project_args = {
        'name': name,
        'description': description,
        'created_by': user,
        'deprecated_project_id': _slugify(name),
    }
    if genome_version:
        project_args['genome_version'] = genome_version

    project, _ = get_or_create_seqr_model(Project, **project_args)

    if settings.PHENOTIPS_SERVER:
        try:
            _enable_phenotips_for_project(project)
        except Exception as e:
            logger.error("Unable to create patient in PhenoTips. Make sure PhenoTips is running: %s", e)
            raise

    # TODO: add custom populations

    return project


def delete_project(project):
    """Delete project.

    Args:
        project (object): Django ORM model for the project to delete
    """

    Sample.objects.filter(individual__family__project=project).delete()
    for individual in Individual.objects.filter(family__project=project):
        delete_seqr_model(individual)
    for family in Family.objects.filter(project=project):
        delete_seqr_model(family)

    delete_seqr_model(project)

    # TODO delete PhenoTips, etc. and other objects under this project


def _enable_phenotips_for_project(project):
    """Creates 2 users in PhenoTips for this project (one that will be view-only and one that'll
    have edit permissions for patients in the project).
    """
    project.is_phenotips_enabled = True
    project.phenotips_user_id = _slugify(project.name)

    # view-only user
    username, password = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    create_phenotips_user(username, password)

    # user with edit permissions
    username, password = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    create_phenotips_user(username, password)
    project.save()
