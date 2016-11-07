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

