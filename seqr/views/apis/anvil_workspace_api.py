"""APIs for management of projects related to AnVIL workspaces."""

import logging
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from seqr.models import Project
from seqr.views.utils.json_to_orm_utils import create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.views.utils.terra_api_utils import is_google_authenticated, user_get_workspace_access_level, add_service_account
from seqr.views.apis.individual_api import _add_or_update_individuals_and_families
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
    Redirect to the loading data from workspace page or redirect to the project if the project exists.

    Validate the workspace and project before loading data.

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
    Create a project when a cooperator requests to load data from an AnVIL workspace.

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return the projectsByGuid with the new project json
    """
    # Validate that the current user has logged in through google and has one of the valid can_edit levels of
    #  access on the specified workspace
    project = Project.objects.filter(name = name)
    if project:
        error = 'Project {} exists.'.format(name)
        return create_json_response({'error': error}, status=400, reason=error)

    if not _workspace_can_edit(request.user, namespace, name):
        return create_json_response({
            'projectsByGuid': {},
        })

    # Validate all the user inputs from the post body
    request_json = json.loads(request.body)

    missing_fields = [field for field in ['genomeVersion', 'uploadedFileId'] if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    if not request_json.get('agreeSeqrAccess'):
        error = 'Must agree to grant seqr access to the data in the associated workspace.'
        return create_json_response({'error': error}, status = 400, reason = error)

    # Add the seqr service account to the corresponding AnVIL workspace
    if add_service_account(request.user, namespace, name):
        # Create a new Project in seqr
        project_args = {
            'name': name,
            'genome_version': request_json['genomeVersion'],
            'description': request_json.get('description', ''),
            'workspace_namespace': namespace,
            'workspace_name': name,
        }

        project = create_model_from_json(Project, project_args, user = request.user)

        # Add families/individuals based on the uploaded pedigree file
        try:
            json_records = load_uploaded_file(request_json['uploadedFileId'])
        except Exception as ee:
            error = "Uploaded pedigree file is missing or other exception: {}".format(str(ee))
            return create_json_response({'error': error}, status = 400, reason = error)

        # todo: update families and individuals according to the uploaded individual records
        updated_families, updated_individuals = _add_or_update_individuals_and_families(
            project, individual_records = json_records, user = request.user
        )

        # todo: Send an email to all seqr data managers saying a new AnVIL project is ready for loading. Include the seqr
        # project guid, the workspace name, and attach a txt file with a list of the individual IDs that were created.
        return create_json_response({'projectGuid':  project.guid})

    error = 'Failed to grant seqr service account access to the workspace'
    return create_json_response({'error': error}, status = 400, reason = error)
