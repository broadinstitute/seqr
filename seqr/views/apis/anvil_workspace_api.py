"""APIs for management of projects related to AnVIL workspaces."""

import logging
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from seqr.models import Project
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.terra_api_utils import is_google_authenticated, user_get_workspace_access_level
from settings import API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


def _workspace_can_edit(user, namespace, name):
    if not is_google_authenticated(user):
        return False
    permission = user_get_workspace_access_level(user, namespace, name)
    if not permission.get('pending') and permission.get('accessLevel') in ['WRITER', 'OWNER', 'PROJECT_OWNER']:
        return True
    return False


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def anvil_workspace_page(request, namespace, name):
    """
    Redirect to the loading data from workspace page or redirect to the project if the project exists

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return Redirect to a page depending on if the workspace permissions or project exists
    Error page if the workspace doesn't exist or the user doesn't have a WRITER permission.
    Redirect to '/create_project_from_workspace/:workspace_namespace/:workspace_name' if
    project doesn't exist. Redirect to '/project/:projectGuid'

    """
    if _workspace_can_edit(request.user, namespace, name):
        project = Project.objects.filter(name=name)
        if project:
            return redirect('/project/{}'.format(project.guid))
        else:
            return redirect('/create_project_from_workspace/{}/{}'.format(namespace, name))
    return {"Error: Workspace {}/{} doesn't exist or misses required permissions (e.g. WRITER, OWNER, or PROJECT_OWNER)"
                .format(namespace, name)}


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_project_from_workspace(request, namespace, name):
    """
    Create a project when a cooperator requesting to load data from an AnVIL workspace

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return the projectsByGuid with the new project json

    """
    response_json = {}  # to be done
    # Validate that the current user has logged in through google and has one of the valid can_edit levels of
    #  access on the specified workspace
    if not _workspace_can_edit(request.user, namespace, name):
        return create_json_response({
            'projectsByGuid': {},
        })

    # Validate all the user input from the post body
    request_json = json.loads(request.body)
    print(request_json)
    error = ''
    if not request_json.get('genomeVersion'):
        error = 'Must choose or genome version.'
    elif not request_json.get('agreeSeqrAccess'):
        error = 'Must agree to grant seqr access to the data in the associated workspace.'
    elif not request_json.get('uploadedFileId'):
        error = 'An individual pedigree file must be uploaded.'

    if error:
        return create_json_response({'Errors': error}, status=403, reason=error)

    # 3) Add the seqr service account to the corresponding AnVIL workspace, so that our team will have access to the
    # project for data loading;
    # 4) Create a new Project in seqr. This project should NOT be added to the analyst group. The project name should
    #  just be the workspace name. Make sure to set workspace_namespace and workspace_name correctly;
    # 5) Add families/individuals based on the uploaded pedigree file;
    # 6) Send an email to all seqr data managers saying a new AnVIL project is ready for loading. Include the seqr
    #  project guid, the workspace name, and attach a txt file with a list of the individual IDs that were created.

    return create_json_response(response_json)
