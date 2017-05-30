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

    return create_json_response({
        family.guid: _get_json_for_family(family, request.user)
    })

