import json
import logging

from django.contrib.auth.decorators import login_required

from seqr.views.utils import get_user_info, render_with_initial_json, create_json_response
from seqr.models import Project

logger = logging.getLogger(__name__)


@login_required
def dashboard_page(request):
    initial_json = json.loads(
        dashboard_page_data(request).content
    )

    return render_with_initial_json('dashboard.html', initial_json)


@login_required
def dashboard_page_data(request):

    # get all projects this user has permissions to view
    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)

    #projects.prefetch_related()

    json_response = {
        'user': get_user_info(request.user),
        'projectsByGuid': {
            p.id: p.json() for p in projects
        },
    }

    return create_json_response(json_response)

