"""
APIs used to retrieve and modify Individual fields
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_to_orm_utils import update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.models import Family, CAN_EDIT

from xbrowse_server.base.models import Family as BaseFamily

logger = logging.getLogger(__name__)

@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_family_field(request, family_guid, field_name):
    """Updates the `case_review_discussion` field for the given family.

    Args:
        family_guid (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)

    # check permission
    project = family.project
    if not request.user.is_staff and not request.user.has_perm(CAN_EDIT, project):
        raise PermissionDenied("%s does not have EDIT permissions for %s" % (request.user, project))

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key")

    family_json = {field_name: request_json['value']}
    update_family_from_json(family, family_json)

    try:
        base_family = BaseFamily.objects.filter(project__project_id=project.deprecated_project_id, family_id=family.family_id)
        base_family = base_family[0]
        value = request_json['value']
        if field_name == "description":
            base_family.short_description = value
        elif field_name == "analysisNotes":
            base_family.about_family_content = value
        elif field_name == "analysisSummary":
            base_family.analysis_summary_content = value
        base_family.save()
    except Exception as e:
        logger.error("Unable to update Base Family")
        logger.error(e)

    return create_json_response({
        family.guid: _get_json_for_family(family, request.user)
    })

