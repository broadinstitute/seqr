"""
APIs used by the case review page
"""

import logging

from django.contrib.admin.views.decorators import staff_member_required

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.family_api import export_families
from seqr.views.apis.individual_api import export_individuals
from seqr.models import Individual, _slugify
from seqr.views.utils.permissions_utils import get_project_and_check_permissions

logger = logging.getLogger(__name__)


def _convert_html_to_plain_text(html_string):
    if not html_string:
        return ''

    return html_string.replace('&nbsp;', '').replace('<div>', '').replace('</div>', '\n')


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def export_case_review_families_handler(request, project_guid):
    """Export case review Families table.

    Args:
        project_guid (string): GUID of the project for which to export case review family data
    """
    format = request.GET.get('file_format', 'tsv')

    project = get_project_and_check_permissions(project_guid, request.user)

    # get all families in this project that have at least 1 individual in case review.
    families = set()
    for i in Individual.objects.filter(family__project=project, case_review_status__regex="[\w].*").order_by('family__family_id'):
        families.add(i.family)

    filename_prefix = "%s_case_review_families" % _slugify(project.name)

    return export_families(filename_prefix, families, format, include_internal_case_review_summary=True, include_internal_case_review_notes=True)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def export_case_review_individuals_handler(request, project_guid):
    """Export case review Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export case review individual data
    """

    format = request.GET.get('file_format', 'tsv')

    project = get_project_and_check_permissions(project_guid, request.user)

    individuals = Individual.objects.filter(family__project=project, case_review_status__regex="[\w].*").order_by('family__family_id', 'affected')

    filename_prefix = "%s_case_review_individuals" % _slugify(project.name)

    return export_individuals(
        filename_prefix,
        individuals,
        format,
        include_case_review_status=True,
        include_case_review_last_modified_date=True,
        include_case_review_last_modified_by=True,
        include_case_review_discussion=True,
        include_hpo_terms_present=True,
        include_hpo_terms_absent=True,
    )
