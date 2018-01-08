"""
APIs used to retrieve and modify Individual fields
"""

import json
import logging
from pprint import pformat

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.individual_api import delete_individuals
from seqr.views.utils.export_table_utils import export_table, _convert_html_to_plain_text
from seqr.views.utils.json_to_orm_utils import update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.models import Family, CAN_EDIT, Individual
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

    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    if 'form' not in request_json:
        return create_json_response(
            {}, status=400, reason="Invalid request: 'form' key not specified")

    form_data = request_json['form']

    modified_families_by_guid = form_data.get('modifiedFamilies')
    if modified_families_by_guid is None:
        return create_json_response(
            {}, status=400, reason="'modifiedIndividuals' not specified")


    # TODO more validation
    #errors, warnings = validate_fam_file_records(modified_individuals_list)
    #if errors:
    #    return create_json_response({'errors': errors, 'warnings': warnings})

    updated_families = []
    for familyGuid, fields in modified_families_by_guid.items():
        family = Family.objects.get(project=project, guid=familyGuid)
        update_family_from_json(family, fields)
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

    if 'form' not in request_json:
        return create_json_response(
            {}, status=400, reason="Invalid request: 'form' not in request_json")

    logger.info("delete_families_handler %s", request_json)

    form_data = request_json['form']

    family_guids_to_delete = form_data.get('recordIdsToDelete')
    if family_guids_to_delete is None:
        return create_json_response(
            {}, status=400, reason="'recordIdsToDelete' not specified")

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
def update_family_field_handler(request, family_guid, field_name):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
        field_name (string): Family model field name to update
    """

    family = Family.objects.get(guid=family_guid)

    # check permission
    project = family.project

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key: %s" % (request.body,))

    value = request_json['value']
    family_json = {field_name: value}
    update_family_from_json(family, family_json)

    _deprecated_update_original_family_field(project, family, field_name, value)

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


def export_families(
        filename_prefix,
        families,
        file_format,
        include_project_name=False,
        include_internal_case_review_summary=False,
        include_internal_case_review_notes=False,
):
    """Export Families table.

    Args:
        filename_prefix (string): Filename wihtout
        families (list): List of Django Family objects to include in the table
        file_format (string): "xls" or "tsv"

    Returns:
        Django HttpResponse object with the table data as an attachment.
    """
    header = []

    if include_project_name:
        header.append('Project')

    header.extend([
        'Family ID',
        'Display Name',
        'Created Date',
        'Description',
        'Analysis Status',
        'Analysis Summary',
        'Analysis Notes',
    ])

    if include_internal_case_review_summary:
        header.append('Internal Case Review Summary')
    if include_internal_case_review_notes:
        header.append('Internal Case Review Notes')

    rows = []
    analysis_status_lookup = dict(Family.ANALYSIS_STATUS_CHOICES)
    for family in families:
        row = []
        if include_project_name:
            row.append(family.project.name or family.project.project_id)

        row.extend([
            family.family_id,
            family.display_name,
            family.created_date,
            family.description,
            analysis_status_lookup.get(family.analysis_status, family.analysis_status),
            _convert_html_to_plain_text(
                family.analysis_summary,
                remove_line_breaks=(file_format == 'tsv')),
            _convert_html_to_plain_text(
                family.analysis_notes,
                remove_line_breaks=(file_format == 'tsv')),
        ])

        if include_internal_case_review_summary:
            row.append(
                _convert_html_to_plain_text(
                    family.internal_case_review_summary,
                    remove_line_breaks=(file_format == 'tsv')),
            )
        if include_internal_case_review_notes:
            row.append(
                _convert_html_to_plain_text(
                    family.internal_case_review_notes,
                    remove_line_breaks=(file_format == 'tsv')),
            )

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)
