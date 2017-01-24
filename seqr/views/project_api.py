import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, CAN_EDIT
from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import create_json_response, _get_json_for_project


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_info(request, project_guid):
    """Modify Project fields.

    Args:
        project_guid (string): GUID of the project.
    """

    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_EDIT, project) and not request.user.is_staff:
        raise PermissionDenied

    request_json = json.loads(request.body)
    form_data = request_json['form']

    project.name = form_data.get('name', project.name)
    project.description = form_data.get('description', project.description)
    project.project_category = form_data.get('project_category', project.project_category)
    project.save()

    return create_json_response({project.guid: _get_json_for_project(project, request.user.is_staff)})
