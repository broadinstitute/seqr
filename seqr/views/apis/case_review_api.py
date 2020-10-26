"""
APIs used by the case review page
"""
import json

from django.contrib.admin.views.decorators import staff_member_required

from seqr.views.utils.json_to_orm_utils import update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.models import Family
from settings import API_LOGIN_REQUIRED_URL


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def save_internal_case_review_notes(request, family_guid):
    """Updates the `case_review_notes` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key: %s" % (request.body,))

    update_family_from_json(family, {'internal_case_review_notes': request_json['value']}, request.user)

    return create_json_response({family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True)})


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def save_internal_case_review_summary(request, family_guid):
    """Updates the `internal_case_review_summary` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key: %s" % (request.body,))

    update_family_from_json(family, {'internal_case_review_summary': request_json['value']}, request.user)
    
    return create_json_response({family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True)})


