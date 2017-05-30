"""
APIs used by the case review page
"""

import json
import logging

from django.contrib.admin.views.decorators import staff_member_required

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.export_table_utils import export_table, export_families, export_individuals
from seqr.views.utils.json_utils import render_with_initial_json, create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, \
    _get_json_for_project, \
    _get_json_for_family, \
    _get_json_for_individual
from seqr.models import Family, Individual, _slugify
from seqr.views.utils.request_utils import _get_project_and_check_permissions

logger = logging.getLogger(__name__)


@staff_member_required
def case_review_page(request, project_guid):
    """Generates the case review page, with initial case_review_page_data json embedded.

    Args:
        project_guid (string): GUID of the Project under case review.
    """

    initial_json = json.loads(
        case_review_page_data(request, project_guid).content
    )

    return render_with_initial_json('case_review.html', initial_json)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def case_review_page_data(request, project_guid):
    """Returns a JSON object containing information used by the case review page:
    ::

      json_response = {
         'user': {..},
         'project': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
       }
    Args:
        project_guid (string): GUID of the project being case-reviewed.
    """

    # get all families in this project
    project = _get_project_and_check_permissions(project_guid, request.user)

    json_response = {
        'user': _get_json_for_user(request.user),
        'project': _get_json_for_project(project, request.user),
        'familiesByGuid': {},
        'individualsByGuid': {},
    }

    for i in Individual.objects.select_related('family').filter(family__project=project):

        # filter out individuals that were never in case review
        if not i.case_review_status:
            continue

        # process family record if it hasn't been added already
        family = i.family
        if family.guid not in json_response['familiesByGuid']:
            json_response['familiesByGuid'][family.guid] = _get_json_for_family(family, request.user)
            json_response['familiesByGuid'][family.guid]['individualGuids'] = []

        json_response['individualsByGuid'][i.guid] = _get_json_for_individual(i, request.user)
        json_response['familiesByGuid'][family.guid]['individualGuids'].append(i.guid)

    return create_json_response(json_response)


def _convert_html_to_plain_text(html_string):
    if not html_string:
        return ''

    return html_string.replace('&nbsp;', '').replace('<div>', '').replace('</div>', '\n')


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def export_case_review_families(request, project_guid):
    """Export case review Families table.

    Args:
        project_guid (string): GUID of the project for which to export case review family data
    """
    format = request.GET.get('file_format', 'tsv')

    project = _get_project_and_check_permissions(project_guid, request.user)

    # get all families in this project that have at least 1 individual in case review.
    families = set()
    for i in Individual.objects.filter(family__project=project, case_review_status__regex="[\w].*").order_by('family__family_id'):
        families.add(i.family)

    filename_prefix = "%s_case_review_families" % _slugify(project.name)

    return export_families(filename_prefix, families, format, include_case_review_columns=True)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def export_case_review_individuals(request, project_guid):
    """Export case review Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export case review individual data
    """

    format = request.GET.get('file_format', 'tsv')

    project = _get_project_and_check_permissions(project_guid, request.user)

    individuals = Individual.objects.filter(family__project=project, case_review_status__regex="[\w].*").order_by('family__family_id', 'affected')

    filename_prefix = "%s_case_review_individuals" % _slugify(project.name)

    return export_individuals(filename_prefix, individuals, format, include_case_review_columns=True, include_phenotips_columns=True)
