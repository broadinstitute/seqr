"""
APIs used to retrieve and modify Individual fields
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.individual_api import delete_individuals

from seqr.views.utils.json_to_orm_utils import update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.models import Family, FamilyAnalysedBy, CAN_EDIT, Individual
from seqr.model_utils import create_seqr_model
from seqr.views.utils.permissions_utils import check_permissions, get_project_and_check_permissions

from xbrowse_server.base.models import Family as BaseFamily

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def edit_families_handler(request, project_guid):
    """Edit or one or more Family records.

    Args:
        project_guid (string): GUID of project that contains these individuals.
    """

    request_json = json.loads(request.body)

    modified_families = request_json.get('families')
    if modified_families is None:
        return create_json_response(
            {}, status=400, reason="'families' not specified")

    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    # TODO more validation
    #errors, warnings = validate_fam_file_records(modified_individuals_list)
    #if errors:
    #    return create_json_response({'errors': errors, 'warnings': warnings})

    updated_families = []
    for fields in modified_families:
        family = Family.objects.get(project=project, guid=fields['familyGuid'])
        update_family_from_json(family, fields, user=request.user, allow_unknown_keys=True)
        updated_families.append(family)

        for key, value in fields.items():
            # TODO do this more efficiently
            _deprecated_update_original_family_field(project, family, key, value)

    updated_families_by_guid = {
        'familiesByGuid': {
            family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True) for family in updated_families
        }
    }

    return create_json_response(updated_families_by_guid)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_families_handler(request, project_guid):
    """Edit or delete one or more Individual records.

    Args:
        project_guid (string): GUID of project that contains these individuals.
    """

    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    logger.info("delete_families_handler %s", request_json)

    families_to_delete = request_json.get('families')
    if families_to_delete is None:
        return create_json_response(
            {}, status=400, reason="'recordIdsToDelete' not specified")
    family_guids_to_delete = [f['familyGuid'] for f in families_to_delete]

    # delete individuals 1st
    individual_guids_to_delete = [i.guid for i in Individual.objects.filter(
        family__project=project, family__guid__in=family_guids_to_delete)]
    delete_individuals(project, individual_guids_to_delete)

    # delete families
    for family in Family.objects.filter(project=project, guid__in=family_guids_to_delete):
        base_family = BaseFamily.objects.get(
            project__project_id=project.deprecated_project_id,
            family_id=family.family_id)
        base_family.delete()

        family.delete()

    # send response
    return create_json_response({
        'individualsByGuid': {
            individual_guid: None for individual_guid in individual_guids_to_delete
        },
        'familiesByGuid': {
            family_guid: None for family_guid in family_guids_to_delete
        },
    })


def _deprecated_update_original_family_fields(project, family, fields):
    # also update base family
    base_family = BaseFamily.objects.filter(
        project__project_id=project.deprecated_project_id, family_id=family.family_id)
    base_family = base_family[0]
    update_family_from_json(base_family, fields)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_family_fields_handler(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)

    # check permission
    project = family.project

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    update_family_from_json(family, request_json, user=request.user, allow_unknown_keys=True)

    return create_json_response({
        family.guid: _get_json_for_family(family, request.user)
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_family_analysed_by(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
        field_name (string): Family model field name to update
    """

    family = Family.objects.get(guid=family_guid)
    check_permissions(family.project, request.user, CAN_EDIT)

    create_seqr_model(FamilyAnalysedBy, family=family, created_by=request.user)

    return create_json_response({
        family.guid: _get_json_for_family(family, request.user)
    })


def _deprecated_update_original_family_field(project, family, field_name, value):
    base_family = BaseFamily.objects.filter(
        project__project_id=project.deprecated_project_id, family_id=family.family_id)
    base_family = base_family[0]
    if field_name == "description":
        base_family.short_description = value
    elif field_name == "analysisNotes":
        base_family.about_family_content = value
    elif field_name == "analysisSummary":
        base_family.analysis_summary_content = value
    elif field_name == "codedPhenotype":
        base_family.coded_phenotype = value
    elif field_name == "postDiscoveryOmimNumber":
        base_family.post_discovery_omim_number = value
    base_family.save()
