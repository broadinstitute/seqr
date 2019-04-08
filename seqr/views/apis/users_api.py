import itertools
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import get_projects_user_can_view


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_all_collaborators(request):
    collaborators = {}
    for project in get_projects_user_can_view(request.user):
        collaborators.update(get_project_collaborators(project, include_permissions=False))

    return create_json_response(collaborators)


def get_project_collaborators(project, include_permissions=True):
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
        'displayName': collaborator.profile.display_name, # TODO use get_full_name() and deprecate profile
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
