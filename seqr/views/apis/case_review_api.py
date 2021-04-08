"""
APIs used by the case review page
"""
import json

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family, _get_json_for_individual
from seqr.views.utils.permissions_utils import has_case_review_permissions, login_and_policies_required
from seqr.models import Family, Individual


@login_and_policies_required
def save_internal_case_review_notes(request, family_guid):
    return _update_family_case_review(family_guid, request, 'caseReviewNotes')

@login_and_policies_required
def save_internal_case_review_summary(request, family_guid):
    return _update_family_case_review(family_guid, request, 'caseReviewSummary')

@login_and_policies_required
def update_case_review_discussion(request, individual_guid):
    return _update_individual_case_review(individual_guid, request, 'caseReviewDiscussion')

@login_and_policies_required
def update_case_review_status(request, individual_guid):
    return _update_individual_case_review(individual_guid, request, 'caseReviewStatus', additional_updates={
        'caseReviewStatusLastModifiedBy': request.user,
        'caseReviewStatusLastModifiedDate': timezone.now(),
    })

def _update_case_review(model, project, request, field, get_response_json, additional_updates=None):
    if not has_case_review_permissions(project, request.user):
        raise PermissionDenied('User cannot edit case review for this project')

    update_json = {field: json.loads(request.body).get(field)}
    if additional_updates:
        update_json.update(additional_updates)

    update_model_from_json(model, update_json, user=request.user)

    return create_json_response({
        model.guid: get_response_json(model, request.user)
    })

def _update_family_case_review(family_guid, request, field):
    family = Family.objects.get(guid=family_guid)
    project = family.project

    return _update_case_review(family, project, request, field, _get_json_for_family)

def _update_individual_case_review(individual_guid, request, field, additional_updates=None):
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project

    return _update_case_review(
        individual, project, request, field, _get_json_for_individual, additional_updates=additional_updates)
