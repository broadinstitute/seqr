"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, _slugify, CAN_EDIT, IS_OWNER
from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.json_utils import create_json_response, _get_json_for_project

from xbrowse_server.base.models import Project as BaseProject


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

    project = Project.objects.create(created_by=request.user, name=name, description=description)

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_project, created = BaseProject.objects.get_or_create(
            project_id=_slugify(name)
        )
        if created:
            print("Created project %s" % base_project)
        base_project.project_name=name
        base_project.description=description
        base_project.save()

        project.deprecated_project_id = base_project.project_id
        project.save()
    except:
        raise

    projects_by_guid = {
        project.guid: _get_json_for_project(project, request.user)
    }

    return create_json_response({
        'projectsByGuid': projects_by_guid,
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
    elif 'description' in form_data:
        project.description = form_data.get('description')
        project.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_project = BaseProject.objects.filter(project_id=project.deprecated_project_id)
        if base_project:
            base_project = base_project[0]
            if 'name' in form_data:
                base_project.project_name = form_data.get('name')
                base_project.save()
            elif 'description' in form_data:
                base_project.description = form_data.get('description')
                base_project.save()
    except:
        raise

    projects_by_guid = {
        project.guid: _get_json_for_project(project, request.user)
    }

    return create_json_response({
        'projectsByGuid': projects_by_guid,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project(request, project_guid):
    """Delete project

    Args:
        project_guid (string): GUID of the project to delete
    """

    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(IS_OWNER, project) and not request.user.is_staff:
        raise PermissionDenied

    project.delete()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_project = BaseProject.objects.filter(project_id=project.deprecated_project_id)
        if base_project:
            base_project = base_project[0]
            base_project.delete()
    except:
        raise

    # TODO delete Family, Individual, and other objects under this project
    return create_json_response({
        'projectsByGuid': {
            project.guid: None
        },
    })




