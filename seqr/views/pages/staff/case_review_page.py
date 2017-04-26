"""
APIs used by the case review page
"""

import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.export_table_utils import export_table, export_families, export_individuals
from seqr.views.utils.json_utils import \
    _get_json_for_user, \
    _get_json_for_project, \
    _get_json_for_family, \
    _get_json_for_individual, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project, Family, Individual, _slugify

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

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
         'familyGuidToIndivGuids': {..},
       }
    Args:
        project_guid (string): GUID of the project being case-reviewed.
    """

    # get all families in this project
    project = Project.objects.filter(guid=project_guid)
    if not project:
        raise ValueError("Invalid project GUID: %s" % project_guid)

    project = project[0]
    json_response = {
        'user': _get_json_for_user(request.user),
        'project': _get_json_for_project(project, request.user),
        'familiesByGuid': {},
        'individualsByGuid': {},
        'familyGuidToIndivGuids': {},
    }

    for i in Individual.objects.select_related('family').filter(family__project=project):

        # filter out individuals that were never in case review
        if not i.case_review_status:
            continue

        # process family record if it hasn't been added already
        family = i.family
        if str(family.guid) not in json_response['familiesByGuid']:
            json_response['familiesByGuid'][family.guid] = _get_json_for_family(family)
            json_response['familyGuidToIndivGuids'][family.guid] = []

        json_response['familyGuidToIndivGuids'][family.guid].append(i.guid)
        json_response['individualsByGuid'][i.guid] = _get_json_for_individual(i)

    return create_json_response(json_response)


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
    responseJSON = {}
    for individual_guid, new_case_review_status in requestJSON['form'].items():
        i = Individual.objects.get(guid=individual_guid)
        if i.case_review_status == new_case_review_status:
            continue
        i.case_review_status = new_case_review_status
        i.case_review_status_last_modified_by = request.user
        i.case_review_status_last_modified_date = timezone.now()
        i.save()

        responseJSON[i.guid] = _get_json_for_individual(i)

        # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
        try:
            base_project = BaseProject.objects.filter(project_id=i.family.project.deprecated_project_id)
            if base_project:
                base_project = base_project[0]
                base_i = BaseIndividual.objects.get(family__project=base_project, indiv_id=i.individual_id)
                base_i.case_review_status = new_case_review_status
                base_i.save()
        except Exception as e:
            raise

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

    family.internal_case_review_notes = requestJSON['form']
    family.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_f = BaseFamily.objects.get(project__project_id=family.project.deprecated_project_id, family_id=family.family_id)
        base_f.internal_case_review_notes = requestJSON['form']
        base_f.save()
    except:
        raise

    return create_json_response({family.guid: _get_json_for_family(family)})


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_internal_case_review_summary(request, family_guid):
    """Updates the `internal_case_review_summary` field for the given family.

    Args:
        family_guid  (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)
    requestJSON = json.loads(request.body)

    family.internal_case_review_brief_summary = requestJSON['form']
    family.save()

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models - TODO remove this code after transition to new schema is finished
    try:
        base_f = BaseFamily.objects.get(project__project_id=family.project.deprecated_project_id, family_id=family.family_id)
        base_f.internal_case_review_brief_summary = requestJSON['form']
        base_f.save()
    except:
        raise

    return create_json_response({family.guid: _get_json_for_family(family)})


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

    project = Project.objects.filter(guid=project_guid)
    if not project:
        raise ValueError("Invalid project GUID: %s" % project_guid)
    project = project[0]

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

    project = Project.objects.filter(guid=project_guid)
    if not project:
        raise ValueError("Invalid project GUID: %s" % project_guid)
    project = project[0]

    individuals = Individual.objects.filter(family__project=project, case_review_status__regex="[\w].*").order_by('family__family_id', 'affected')

    filename_prefix = "%s_case_review_individuals" % _slugify(project.name)

    return export_individuals(filename_prefix, individuals, format, include_case_review_columns=True, include_phenotips_columns=True)
