import json
import logging

from django.contrib.auth.decorators import login_required

from seqr.views.auth_api import API_LOGIN_REDIRECT_URL
from seqr.views.utils import \
    _get_json_for_user, \
    _get_json_for_project, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project

logger = logging.getLogger(__name__)


@login_required
def dashboard_page(request):
    """Generates the dashboard page, with initial dashboard_page_data json embedded."""

    initial_json = json.loads(
        dashboard_page_data(request).content
    )

    return render_with_initial_json('dashboard.html', initial_json)


@login_required(login_url=API_LOGIN_REDIRECT_URL)
def dashboard_page_data(request):
    """Returns a JSON object containing information used by the case review page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'familyGuidToIndivGuids': {..},
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """

    # get all projects this user has permissions to view
    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)

    #projects.prefetch_related()

    json_response = {
        'user': _get_json_for_user(request.user),
        'projectsByGuid': {
            p.guid: _get_json_for_project(p) for p in projects
        },
    }

    return create_json_response(json_response)

