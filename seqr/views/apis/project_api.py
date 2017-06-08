"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, _slugify, CAN_EDIT, IS_OWNER, Family, Individual
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.phenotips_api import create_phenotips_user, _get_phenotips_uname_and_pwd_for_project
from seqr.views.apis.variant_tag_api import _add_default_variant_tag_types
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_project
from seqr.views.utils.request_utils import _get_project_and_check_permissions

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

logger = logging.getLogger(__name__)


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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_project(request):
    """Create a new project.

    HTTP POST
        Request body - should contain json params:
            name: Project name
            description: Project description

        Response body - will be json with the following structure, representing the created project:
            {
                'projectsByGuid':  { <projectGuid1> : { ... <project key-value pairs> ... } }
            }

    """
    request_json = json.loads(request.body)
    if 'form' not in request_json:
        return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")

    form_data = request_json['form']

    name = form_data.get('name')
    if not name:
        return create_json_response({}, status=400, reason="'Name' cannot be blank")

    description = form_data.get('description')

    project, created = Project.objects.get_or_create(created_by=request.user, name=name, description=description)
    if not created:
        return create_json_response({}, status=400, reason="A project named '%(name)s' already exists" % locals())

    base_project = _deprecated_create_original_project(project)
    project.deprecated_project_id = base_project.project_id
    project.save()

    _enable_phenotips_for_project(project)
    _add_default_variant_tag_types(project)

    # TODO: add custom populations

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project(request, project_guid):
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

    # check permissions
    if not request.user.has_perm(CAN_EDIT, project) and not request.user.is_staff:
        raise PermissionDenied

    request_json = json.loads(request.body)
    if 'form' not in request_json:
        return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")

    form_data = request_json['form']
    if 'name' in form_data:
        project.name = form_data.get('name')
        project.save()
    if 'description' in form_data:
        project.description = form_data.get('description')
        project.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    _deprecated_update_original_project(project)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project(request, project_guid):
    """Delete project

    Args:
        project_guid (string): GUID of the project to delete
    """

    project = _get_project_and_check_permissions(project_guid, request.user, permission_level=IS_OWNER)

    _deprecated_delete_original_project(project)

    for family in Family.objects.filter(project=project):
        for individual in Individual.objects.filter(family=family):
            individual.delete()
        family.delete()
    project.delete()

    # TODO delete PhenoTips, etc. and other objects under this project

    return create_json_response({
        'projectsByGuid': {
            project.guid: None
        },
    })


def _deprecated_create_original_project(project):
    """DEPRECATED - create project in original xbrowse schema to keep things in sync.

    Args:
        project (object): new-style seqr project model
    """

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models
    base_project, created = BaseProject.objects.get_or_create(
        project_id=_slugify(project.name)
    )

    if created:
        logger.info("Created base project %s" % base_project)

    base_project.project_name = project.name
    base_project.description = project.description
    base_project.save()

    return base_project


def _deprecated_update_original_project(project):
    """DEPRECATED - update project in original xbrowse schema to keep things in sync.
    Args:
        project (object): new-style seqr project model
    """

    base_project = BaseProject.objects.filter(project_id=project.deprecated_project_id)
    if base_project:
        base_project = base_project[0]
        base_project.project_name = project.name
        base_project.description = project.description
        base_project.save()


def _deprecated_delete_original_project(project):
    """DEPRECATED - delete project in original xbrowse schema to keep things in sync.
    Args:
        project (object): new-style seqr project model
    """

    base_project = BaseProject.objects.filter(project_id=project.deprecated_project_id)
    if base_project:
        base_project = base_project[0]
        for base_family in BaseFamily.objects.filter(project=base_project):
            for base_individual in BaseIndividual.objects.filter(family=base_family):
                base_individual.delete()
            base_family.delete()
        base_project.delete()



