"""APIs for management of projects related to AnVIL workspaces."""

import logging
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from seqr.models import Project, CAN_EDIT
from seqr.views.utils.json_to_orm_utils import create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.views.utils.terra_api_utils import add_service_account
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from seqr.views.apis.individual_api import _add_or_update_individuals_and_families
from seqr.utils.communication_utils import send_load_data_email
from seqr.views.utils.permissions_utils import google_auth_required, workspace_has_perm
from settings import API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


def get_project_name(namespace, name):
    return '{} - {}'.format(namespace, name)


@google_auth_required
def anvil_workspace_page(request, namespace, name):
    """
    Validate the workspace and project before loading data.

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return Redirect to a page depending on if the workspace permissions or project exists
    """
    if not workspace_has_perm(request.user, CAN_EDIT, namespace, name, can_share=True):
        message = "Missing required permissions for loading data from workspace {}/{}".format(namespace, name)
        logger.warning(message)
        return create_json_response({'error': message}, status=400, reason=message)

    project_name = get_project_name(namespace, name)
    project = Project.objects.filter(name=project_name)
    if project:
        return redirect('/project/{}/project_page'.format(project.first().guid))
    else:
        return redirect('/create_project_from_workspace/{}/{}'.format(namespace, name))


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_project_from_workspace(request, namespace, name):
    """
    Create a project when a cooperator requests to load data from an AnVIL workspace.

    :param request: Django request object
    :param namespace: The namespace (or the billing account) of the workspace
    :param name: The name of the workspace. It also be used as the project name
    :return the projectsByGuid with the new project json
    """
    project_name = get_project_name(namespace, name)
    project = Project.objects.filter(name = project_name)
    if project:
        error = 'Project {} exists.'.format(project_name)
        logger.warning(error)
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate that the current user has logged in through google and has sufficient permissions
    if not workspace_has_perm(request.user, CAN_EDIT, namespace, name, can_share=True):
        error = "Missing required permissions for loading data from workspace {}/{}".format(namespace, name)
        logger.warning(error)
        return create_json_response({'error': error}, status=400, reason=error)

    # Validate all the user inputs from the post body
    request_json = json.loads(request.body)

    missing_fields = [field for field in ['genomeVersion', 'uploadedFileId'] if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    if not request_json.get('agreeSeqrAccess'):
        error = 'Must agree to grant seqr access to the data in the associated workspace.'
        return create_json_response({'error': error}, status=400, reason=error)

    # Add the seqr service account to the corresponding AnVIL workspace
    add_service_account(request.user, namespace, name)

    # Parse families/individuals in the uploaded pedigree file
    try:
        json_records = load_uploaded_file(request_json['uploadedFileId'])
    except Exception as ee:
        error = "Uploaded pedigree file is missing or other exception: {}".format(str(ee))
        return create_json_response({'error': error}, status=400, reason=error)

    pedigree_records, errors, ped_warnings = parse_pedigree_table(json_records, 'ped_file', user=request.user, project=project)
    if errors:
        error = "Parse pedigree data failed."
        return create_json_response({'error': error}, status=400, reason=error)

    # Create a new Project in seqr
    project_args = {
        'name': project_name,
        'genome_version': request_json['genomeVersion'],
        'description': request_json.get('description', ''),
        'workspace_namespace': namespace,
        'workspace_name': name,
    }

    project = create_model_from_json(Project, project_args, user = request.user)

    # update families and individuals according to the uploaded individual records
    updated_families, updated_individuals = _add_or_update_individuals_and_families(
        project, individual_records = pedigree_records, user = request.user
    )

    # Send an email to all seqr data managers
    info = ['{} families and {} individuals have been added to the new project'
                .format(len(updated_families), len(updated_families))]
    individual_ids = [individual['individualId'] for individual in pedigree_records]
    try:
        send_load_data_email(request.user, project.guid, namespace, name, individual_ids)
    except Exception as ee:
        message = 'Exception while sending email to user {}. {}'.format(request.user, (ee))
        logger.error(message)
        info.append(message)

    return create_json_response({
        'projectGuid':  project.guid,
        'info': info,
    })
