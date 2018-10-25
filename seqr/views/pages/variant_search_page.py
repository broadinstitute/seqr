import logging

from django.contrib.auth.decorators import login_required

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.pages.project_page import get_project_details
from seqr.views.utils.json_utils import create_json_response
from seqr.models import Family

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def variant_search_page_data(request):
    """Returns a JSON object containing information needed to display the variant search page
    ::

      json_response = {
         'user': {..},
         'variants': [..],
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """
    # TODO project, analysisGroup
    # single-family search mode
    family_guid = request.GET.get('familyGuid')
    family = Family.objects.get(guid=family_guid)

    return create_json_response(get_project_details(family.project.guid, request.user))
