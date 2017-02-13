import json
import logging

from django.http import JsonResponse
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.template import loader
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def render_with_initial_json(html_page, initial_json):
    """Uses django template rendering utilities to read in the given html file, and embed the
    given object as json within the page. This way when the browser sends an initial request
    for the page, it comes back with the json bundle already embedded in it.

    Args:
        html_page (string): path of html template
        initial_json (object): the object to be serialized to json
    Returns:
        HttpResponse: django HttpRepsonse object to send back to the client
    """

    initial_json_str = json.dumps(
        initial_json,
        sort_keys=True,
        indent=4,
        default=DateTimeAwareJSONEncoder().default
    )

    html = loader.render_to_string(html_page)

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON="+initial_json_str
    )
    return HttpResponse(html)


def create_json_response(obj, **kwargs):
    """Encodes the give object into json and create a django JsonResponse object with it.

    Args:
        obj (object): json response object
        **kwargs: any addition args to pass to the JsonResponse constructor
    Returns:
        JsonResponse
    """

    dumps_params = {
        'sort_keys': True,
        'indent': 4,
        'default': DateTimeAwareJSONEncoder().default
    }

    return JsonResponse(
        obj, json_dumps_params=dumps_params, encoder=DateTimeAwareJSONEncoder, **kwargs)


def _get_json_for_user(user):
    json_obj = {
        key: value
        for key, value in user._wrapped.__dict__.items()
        if not key.startswith("_") and key != "password"
    }

    return json_obj


def _get_json_for_project(project, user):
    """Returns a json object for the given project.

    Args:
        project (model): django model for the project
        user (object): Django User model  - used to determine permissions for accessing certain fields
    Returns:
        dict: json object
    """
    return {
        'projectGuid': project.guid,
        'name': project.name,
        'description': project.description,
        'createdDate': project.created_date,
        'lastModifiedDate': project.last_modified_date,
        'lastAccessedDate': project.deprecated_last_accessed_date if user.is_staff else None,
        'deprecatedProjectId': project.deprecated_project_id,
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()],
        'isPhenotipsEnabled': project.is_phenotips_enabled,
        'phenotipsUserId': project.phenotips_user_id,
        'isMmeEnabled': project.is_mme_enabled,
        'mmePrimaryDataOwner': project.mme_primary_data_owner,
    }


def _get_json_for_family(family):
    """Returns a json object for the given individual, with all fields that are relevant to the case
    review page.

    Args:
        family (model): django model representing the individual.
    Returns:
        dict: json object
    """

    return {
        'familyGuid':      family.guid,
        'familyId':        family.family_id,
        'displayName':     family.display_name,
        'description':     family.description,
        'analysisNotes':   family.analysis_notes,
        'analysisSummary': family.analysis_summary,
        'pedigreeImage':   family.pedigree_image.url if family.pedigree_image else None,
        'analysisStatus':  family.analysis_status,
        'causalInheritanceMode': family.causal_inheritance_mode,
        'internalCaseReviewNotes': family.internal_case_review_notes,
        'internalCaseReviewSummary': family.internal_case_review_brief_summary,
    }


def _get_json_for_individual(individual):
    """Returns a json object for the given individual, with all fields that are relevant to the case
    review page.

    Args:
        individual (model): django model for the individual.
    Returns:
        dict: json object
    """

    case_review_status_last_modified_by = None
    if individual.case_review_status_last_modified_by:
        u = individual.case_review_status_last_modified_by
        case_review_status_last_modified_by = u.email or u.username

    return {
        'individualGuid': individual.guid,
        'individualId': individual.individual_id,
        'displayName': individual.display_name,
        'paternalId': individual.paternal_id,
        'maternalId': individual.maternal_id,
        'sex': individual.sex,
        'affected': individual.affected,
        'caseReviewStatus': individual.case_review_status,
        'caseReviewStatusLastModifiedBy': case_review_status_last_modified_by,
        'caseReviewStatusLastModifiedDate': individual.case_review_status_last_modified_date,
        'phenotipsPatientId': individual.phenotips_patient_id,
        'phenotipsData': json.loads(individual.phenotips_data) if individual.phenotips_data else None,
        'createdDate': individual.created_date,
        'lastModifiedDate': individual.last_modified_date,
    }




"""
@login_required
def projects(request):
    "Returns information on all projects this user has access to"

    # look up all projects the user has permissions to view
    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)

    return _create_json_response({"projects": [p.json() for p in projects]})


@login_required
def families(request, project_guid):
    # get all families in a particular project


@login_required
def individuals(request):

"""
