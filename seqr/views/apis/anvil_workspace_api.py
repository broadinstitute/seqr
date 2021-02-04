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
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from seqr.views.apis.individual_api import _add_or_update_individuals_and_families
from seqr.utils.communication_utils import send_load_data_email
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
    Validate the workspace and project before loading data.

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return Redirect to a page depending on if the workspace permissions or project exists
    """
    if _workspace_can_edit(request.user, namespace, name):
        project = Project.objects.filter(name=name)
        if project:
            return redirect('/project/{}'.format(project.guid))
        else:
            return redirect('/create_project_from_workspace/{}/{}'.format(namespace, name))
    return {"Workspace {}/{} doesn't exist or misses required permissions (e.g. WRITER, OWNER, or PROJECT_OWNER)"
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
    project = Project.objects.filter(name = name)
    if project:
        error = 'Project {} exists.'.format(name)
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate that the current user has logged in through google and has sufficient permissions
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
    if not add_service_account(request.user, namespace, name):
        error = 'Failed to grant seqr service account access to the workspace'
        return create_json_response({'error': error}, status = 400, reason = error)

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
    pedigree_records, errors, ped_warnings = parse_pedigree_table(json_records, 'ped_file', user=request.user, project=project)
    if errors:
        error = "Parse pedigree data failed."
        return create_json_response({'error': error}, status = 400, reason = error)

    # update families and individuals according to the uploaded individual records
    updated_families, updated_individuals = _add_or_update_individuals_and_families(
        project, individual_records = pedigree_records, user = request.user
    )

    # Send an email to all seqr data managers
    individual_ids = [individual['individualId'] for individual in pedigree_records]
    send_load_data_email(request.user, project.guid, namespace, name, individual_ids)

    return create_json_response({'projectGuid':  project.guid})


