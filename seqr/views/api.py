from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from xbrowse_server.server_utils import HttpResponse
from xbrowse_server.base.models import Project, Family, Individual
from django.db import connection
from django.core.serializers.json import DateTimeAwareJSONEncoder
import json


@login_required
def user(request):
    """Returns user information"""

    json_obj = {key: value for key, value in request.user._wrapped.__dict__.items()
                if not key.startswith("_") and key != "password"}
    json_response_string = json.dumps({"user": json_obj}, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return HttpResponse(json_response_string, content_type="application/json")


@login_required
def projects(request):
    """Returns information on all projects this user has access to"""

    # look up all projects the user has permissions to view
    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(projectcollaborator__user=request.user)

    for project in projects:
        if not project.can_view(request.user):
            raise ValueError  # TODO error handling

    # serialize to json
    json_obj = {"projects": list(projects.values())}
    json_response_string = json.dumps(json_obj, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return HttpResponse(json_response_string, content_type="application/json")


@login_required
def projects_and_stats(request):
    """TODO docs"""

    # TODO check permissions

    #for project in projects:
    #    if not project.can_view(request.user):
    #        raise ValueError  # TODO error handling

    # use raw SQL to compute family and individual counts using nested queries
    cursor = connection.cursor()
    cursor.execute("""
      SELECT
        *,
        (SELECT count(*) FROM base_family WHERE project_id=base_project.id) AS num_families,
        (SELECT count(*) FROM base_individual WHERE project_id=base_project.id) AS num_individuals
      FROM base_project
    """)

    columns = [col[0] for col in cursor.description]
    json_obj = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()

    json_response_string = json.dumps(
            {"projects": json_obj}, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return HttpResponse(json_response_string, content_type="application/json")


"""

@login_required
def families(request, project_id):
    # get all families in a particular project
    if not project.can_view(request.user):
        raise ValueError  # TODO error handling


@login_required
def individuals(request):

    # get all individuals in all projects that this user has permissions to access
    for i in Individual.objects.filter(project__projectcollaborator__user=request.user):
        {
            "affected": i.affected,
            "indivId": i.indiv_id,
            "projectId": i.project.project_id,
            "familyId": i.family.family_id,
            "sex": i.sex,
            "maternalId": i.maternal_id,
            "paternalId": i.paternal_id,
            'hasVariantData': self.has_variant_data(),
            'hasBamFilePath': bool(self.bam_file_path),
        }

@csrf_exempt  # all post requests have CSRF protection
@require_POST
@login_required
def variants(request):
    json_response_string = json.dumps({'results': ['variant1', 'variant2']})
    return HttpResponse(json_response_string, content_type="application/json")


"""

@login_required
def case_review_data(request, project_guid):

    if not request.user.is_staff:
        raise ValueError("Permission denied")

    # get all families in a particular project
    project = Project.objects.filter(id=project_guid)
    if not project:
        raise ValueError("Invalid project id: %s" % project_guid)

    json_response = {
        'familiesByGuid': {},
        'individualsByGuid': {},
        'familyGuidToIndivGuids': {},
    }

    user_json = json.loads(user(request).content)
    json_response.update(user_json)

    project = project[0]
    project_json = {
        'project': {
            'projectGuid': '%s' % project.id,
            'projectId': project.project_id
        }
    }

    json_response.update(project_json)

    for i in Individual.objects.filter(project=project).select_related(
            'family__analysis_status_saved_by'):

        # process family record if it hasn't been added already
        family = i.family
        if str(family.id) not in json_response['familiesByGuid']:
            json_response['familyGuidToIndivGuids']['%s' % family.id] = []

            json_response['familiesByGuid']['%s' % family.id] = {
                'familyGuid':          '%s' % family.id,
                'familyId':            family.family_id,
                'familyName':          family.family_name,
                'shortDescription':    family.short_description,
                'aboutFamilyContent':  family.about_family_content,
                'analysisSummaryContent': family.analysis_summary_content,
                'pedigreeImage':       family.pedigree_image.url if family.pedigree_image else None,
                'analysisStatus': {
                    "status": family.analysis_status,
                    "savedBy" : (family.analysis_status_saved_by.email or family.analysis_status_saved_by.username) if family.analysis_status_saved_by else None,
                    "dateSaved": family.analysis_status_date_saved if family.analysis_status_date_saved else None,
                },
                'causalInheritanceMode': family.causal_inheritance_mode,
                'internalCaseReviewNotes': family.internal_case_review_notes,
                'internalCaseReviewSummary': family.internal_case_review_brief_summary,
            }

        json_response['familyGuidToIndivGuids']['%s' % family.id].append('%s' % i.id)

        json_response['individualsByGuid']['%s' % i.id] = {
            'individualGuid': '%s' % i.id,
            'individualId': i.indiv_id,
            'paternalId': i.paternal_id,
            'maternalId': i.maternal_id,
            'sex': i.gender,
            'affected': i.affected,
            'inCaseReview': i.in_case_review,
            'caseReviewStatus': i.case_review_status,
            'phenotipsId': i.phenotips_id,
            'phenotipsData': json.loads(i.phenotips_data) if i.phenotips_data else None,
        }

    json_response_string = json.dumps(json_response, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return HttpResponse(json_response_string, content_type="application/json")


@login_required
@csrf_exempt
def save_case_review_status(request, project_guid):
    if not request.user.is_staff:
        raise ValueError("Permission denied")

    project = Project.objects.get(id=project_guid)

    requestJSON = json.loads(request.body)
    for individual_guid, value in requestJSON['form'].items():
        i = Individual.objects.get(project=project, id=individual_guid)
        i.case_review_status = value
        i.save()

    return HttpResponse({}, content_type="application/json")


@login_required
@csrf_exempt
def save_internal_case_review_notes(request, project_guid, family_guid):
    if not request.user.is_staff:
        raise ValueError("Permission denied")

    project = Project.objects.get(id=project_guid)
    family = Family.objects.get(project=project, id=family_guid)
    requestJSON = json.loads(request.body)

    family.internal_case_review_notes = requestJSON['form']
    family.save()

    return HttpResponse({}, content_type="application/json")

@login_required
@csrf_exempt
def save_internal_case_review_summary(request, project_guid, family_guid):
    if not request.user.is_staff:
        raise ValueError("Permission denied")

    project = Project.objects.get(id=project_guid)
    family = Family.objects.get(project=project, id=family_guid)
    requestJSON = json.loads(request.body)

    family.internal_case_review_brief_summary = requestJSON['form']
    family.save()

    return HttpResponse({}, content_type="application/json")
