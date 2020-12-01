"""
APIs used by the case review page
"""
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.views.utils.permissions_utils import has_case_review_permissions
from seqr.models import Family
from settings import API_LOGIN_REQUIRED_URL


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def save_internal_case_review_notes(request, family_guid):
    """Updates the `case_review_notes` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    if not has_case_review_permissions(family.project, request.user):
        raise PermissionDenied('User cannot edit case_review_notes for this project')

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key: %s" % (request.body,))

    update_model_from_json(family, {'case_review_notes': request_json['value']}, request.user)

    return create_json_response({family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True)})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def save_internal_case_review_summary(request, family_guid):
    """Updates the `internal_case_review_summary` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    if not has_case_review_permissions(family.project, request.user):
        raise PermissionDenied('User cannot edit case_review_summary for this project')

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key: %s" % (request.body,))

    update_model_from_json(family, {'case_review_summary': request_json['value']}, request.user)
    
    return create_json_response({family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True)})


