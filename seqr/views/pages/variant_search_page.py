import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import render_with_initial_json, create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, _get_json_for_project
from seqr.models import Project, CAN_VIEW
from seqr.views.utils.request_utils import _get_project_and_check_permissions

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def variant_search_page(request, project_guid):
    """Generates the dashboard page, with initial variant_search_page json embedded."""

    # check project permissions
    project = _get_project_and_check_permissions(project_guid, request.user)

    initial_json = json.loads(
        variant_search_page_data(request).content
    )

    return render_with_initial_json('variant_search.html', initial_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def variant_search_page_data(request, project_guid):
    """Returns a JSON object containing information needed to display the variant search page
    ::

      json_response = {
         'user': {..},
         'variants': [..],
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """

    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
        raise PermissionDenied

    json_response = {
        'user': _get_json_for_user(request.user),
        'project': _get_json_for_project(project, request.user),
        'variants': {},
    }

    return create_json_response(json_response)