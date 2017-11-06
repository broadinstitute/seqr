"""
APIs used to retrieve and modify Individual fields
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.export_table_utils import export_table, _convert_html_to_plain_text
from seqr.views.utils.json_to_orm_utils import update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_family
from seqr.models import Family, CAN_EDIT

from xbrowse_server.base.models import Family as BaseFamily

logger = logging.getLogger(__name__)

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
    if not request.user.is_staff and not request.user.has_perm(CAN_EDIT, project):
        raise PermissionDenied("%s does not have EDIT permissions for %s" % (request.user, project))

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key")

    value = request_json['value']
    family_json = {field_name: value}
    update_family_from_json(family, family_json)

    _deprecated_update_original_family_record(project, family, field_name, value)

    return create_json_response({
        family.guid: _get_json_for_family(family, request.user)
    })


def _deprecated_update_original_family_record(project, family, field_name, value):
    base_family = BaseFamily.objects.filter(project__project_id=project.deprecated_project_id, family_id=family.family_id)
    base_family = base_family[0]
    if field_name == "description":
        base_family.short_description = value
    elif field_name == "analysisNotes":
        base_family.about_family_content = value
    elif field_name == "analysisSummary":
        base_family.analysis_summary_content = value
    base_family.save()


def export_families(filename_prefix, families, file_format, include_project_name=False, include_internal_case_review_summary=False, include_internal_case_review_notes=False):
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
    for f in families:
        row = []
        if include_project_name:
            row.append(f.project.name or f.project.project_id)

        row.extend([
            f.family_id,
            f.display_name,
            f.created_date,
            f.description,
            analysis_status_lookup.get(f.analysis_status, f.analysis_status),
            _convert_html_to_plain_text(f.analysis_summary, remove_line_breaks=(file_format == 'tsv')),
            _convert_html_to_plain_text(f.analysis_notes, remove_line_breaks=(file_format == 'tsv')),
        ])

        if include_internal_case_review_summary:
            row.append(_convert_html_to_plain_text(f.internal_case_review_summary, remove_line_breaks=(file_format == 'tsv')),)
        if include_internal_case_review_notes:
            row.append(_convert_html_to_plain_text(f.internal_case_review_notes, remove_line_breaks=(file_format == 'tsv')))

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


