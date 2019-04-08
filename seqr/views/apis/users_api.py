import itertools
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import get_projects_user_can_view, get_project_and_check_permissions, CAN_EDIT


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_all_collaborators(request):
    collaborators = {}
    for project in get_projects_user_can_view(request.user):
        collaborators.update(_get_project_collaborators(project, include_permissions=False))

    return create_json_response(collaborators)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_project_collaborator(request, project_guid):
    raise NotImplementedError


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    user.first_name = request_json.get('firstName') or ''
    user.last_name = request_json.get('lastName') or ''
    user.save()

    project.can_view_group.user_set.add(user)
    if request_json.get('hasEditPermissions'):
        project.can_edit_group.user_set.add(user)
    else:
        project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(project)}}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    user = User.objects.get(username=username)

    project.can_view_group.user_set.remove(user)
    project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(project)}}
    })


def get_json_for_project_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = _get_project_collaborators(project).values()

    return sorted(collaborator_list, key=lambda collaborator: (collaborator['lastName'], collaborator['displayName']))


def _get_project_collaborators(project, include_permissions=True):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborators = {}

    for collaborator in project.can_view_group.user_set.all():
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=False
        )

    for collaborator in itertools.chain(project.owners_group.user_set.all(), project.can_edit_group.user_set.all()):
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=True
        )

    return collaborators


def _get_collaborator_json(collaborator, include_permissions, can_edit):
    collaborator_json = {
        'displayName': collaborator.get_full_name(),
        'username': collaborator.username,
        'email': collaborator.email,
        'firstName': collaborator.first_name,
        'lastName': collaborator.last_name,
    }
    if include_permissions:
        collaborator_json.update({
            'hasViewPermissions': True,
            'hasEditPermissions': can_edit,
        })
    return collaborator_json
