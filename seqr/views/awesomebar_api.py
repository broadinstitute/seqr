"""API for omni-bar auto-complete and search functionality"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.views.decorators.http import require_GET

from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import \
    _get_json_for_user, \
    _get_json_for_project, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project, Family, Individual, LocusList

logger = logging.getLogger(__name__)


@login_required
@require_GET
def awesomebar_autocomplete(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    response = request.GET.get('q', None)

