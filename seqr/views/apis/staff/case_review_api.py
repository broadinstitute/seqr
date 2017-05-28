"""
APIs used by the case review page
"""

import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family, _get_json_for_individual
from seqr.models import Family, Individual
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_case_review_status(request):
    """Updates the `case_review_status` of one or more individuals.

    HTTP POST
        Request body - should contain json:
            {
                form: {
                    <individualGuid1> : <case review status>,
                    <individualGuid2> : <case review status>,
                    ..
                }
            }

        Response body - will be json with the following structure, representing the created project:
            {
                <individualGuid1> : { ... <individual key-value pairs> ... },
            }

    """

    requestJSON = json.loads(request.body)
    if "form" not in requestJSON:
        raise ValueError("Request is missing 'form' key")

    responseJSON = {}
    for individual_guid, case_review_status_change in requestJSON['form'].items():
        i = Individual.objects.get(guid=individual_guid)

        # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
        base_project = BaseProject.objects.filter(project_id=i.family.project.deprecated_project_id)
        if base_project:
            base_project = base_project[0]
            base_i = BaseIndividual.objects.get(family__project=base_project, indiv_id=i.individual_id)

        value = case_review_status_change.get('value')
        action = case_review_status_change.get('action')
        if  action == 'UPDATE_CASE_REVIEW_STATUS':
            if i.case_review_status == value:
                continue

            # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
            i.case_review_status = value
            base_i.case_review_status = i.case_review_status
        elif action == 'ADD_ACCEPTED_FOR':
            if i.case_review_status_accepted_for and (value in i.case_review_status_accepted_for):
                continue

            # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
            i.case_review_status_accepted_for = "".join(sorted(set((i.case_review_status_accepted_for or "") + value)))
            base_i.case_review_status_accepted_for = i.case_review_status_accepted_for
        elif action == 'REMOVE_ACCEPTED_FOR':
            if not i.case_review_status_accepted_for or (value not in i.case_review_status_accepted_for):
                continue

            i.case_review_status_accepted_for = i.case_review_status_accepted_for.replace(value, "")
            base_i.case_review_status_accepted_for = i.case_review_status_accepted_for
        else:
            raise ValueError("Unexpected action param: {0}".format(case_review_status_change.get('action')))

        print("Saving individual: %s %s %s" % ( i.individual_id, i.case_review_status, i.case_review_status_accepted_for))
        i.case_review_status_last_modified_by = request.user
        i.case_review_status_last_modified_date = timezone.now()
        i.save()
        base_i.save()

        responseJSON[i.guid] = _get_json_for_individual(i, request.user)

    return create_json_response(responseJSON)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_internal_case_review_notes(request, family_guid):
    """Updates the `case_review_notes` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    requestJSON = json.loads(request.body)
    if "value" not in requestJSON:
        raise ValueError("Request is missing 'value' key")

    family.internal_case_review_notes = requestJSON['value']
    family.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_f = BaseFamily.objects.get(project__project_id=family.project.deprecated_project_id, family_id=family.family_id)
        base_f.internal_case_review_notes = requestJSON['value']
        base_f.save()
    except:
        raise

    return create_json_response({family.guid: _get_json_for_family(family, request.user)})


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_internal_case_review_summary(request, family_guid):
    """Updates the `internal_case_review_summary` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    requestJSON = json.loads(request.body)
    if "value" not in requestJSON:
        raise ValueError("Request is missing 'value' key")

    family.internal_case_review_summary = requestJSON['value']
    family.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_f = BaseFamily.objects.get(project__project_id=family.project.deprecated_project_id, family_id=family.family_id)
        base_f.internal_case_review_summary = requestJSON['value']
        base_f.save()
    except:
        raise

    return create_json_response({family.guid: _get_json_for_family(family, request.user)})


