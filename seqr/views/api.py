from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from xbrowse_server.server_utils import HttpResponse, JSONResponse
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
            "indiv_id": i.indiv_id,
            "project_id": i.project.project_id,
            "family_id": i.family.family_id,
            "sex": i.sex,
            "maternal_id": i.maternal_id,
            "paternal_id": i.paternal_id,
            'has_variant_data': self.has_variant_data(),
            'has_bam_file_path': bool(self.bam_file_path),
        }

@csrf_exempt  # all post requests have CSRF protection
@require_POST
@login_required
def variants(request):
    json_response_string = json.dumps({'results': ['variant1', 'variant2']})
    return HttpResponse(json_response_string, content_type="application/json")


"""

#@login_required
def case_review_families_and_individuals(request, project_id):
    """Returns user information"""

    #if not request.user.is_staff:
    #    raise ValueError("Permission denied")

    # get all families in a particular project
    project = Project.objects.filter(project_id = project_id)
    if not project:
        raise ValueError("Invalid project id: %s" % project_id)

    json_response = {
        'families_by_id': {},
        'individuals_by_id': {},
        'family_id_to_indiv_ids': {}
    }

    for i in Individual.objects.filter(project=project).select_related(
            'family__analysis_status_saved_by',
            'family__pedigree_image'):

        # process family record if it hasn't been added already
        family = i.family
        if family.id not in json_response['families_by_id']:
            json_response['family_id_to_indiv_ids'][family.id] = []

            json_response['families_by_id'][family.id] = {
                'family_name':          family.family_name,
                'short_description':    family.short_description,
                'about_family_content': family.about_family_content,
                'analysis_summary_content': family.analysis_summary_content,
                'pedigree_image': family.pedigree_image.url if family.pedigree_image else None,
                'analysis_status': {
                    "status": family.analysis_status,
                    "saved_by" : (family.analysis_status_saved_by.email or family.analysis_status_saved_by.username) if family.analysis_status_saved_by else None,
                    "date_saved": family.analysis_status_date_saved if family.analysis_status_date_saved else None,
                },
                'causal_inheritance_mode': family.causal_inheritance_mode,
            }

        json_response['family_id_to_indiv_ids'][family.id].append(i.id)

        json_response['individuals_by_id'][i.id] = {
            'paternal_id': i.paternal_id,
            'maternal_id': i.maternal_id,
            'sex':    i.gender,
            'affected': i.affected,
            'in_case_review': i.in_case_review,
            'case_review_status': i.case_review_status,
        }


    json_response_string = json.dumps(json_response, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return HttpResponse(json_response_string, content_type="application/json")

