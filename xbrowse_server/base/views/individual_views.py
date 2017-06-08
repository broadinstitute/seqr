from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from xbrowse_server.base.models import Project, Individual
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied

@login_required
@log_request('individual_home')
def individual_home(request, project_id, indiv_id):

    project = get_object_or_404(Project, project_id=project_id)
    individual = get_object_or_404(Individual, project=project, indiv_id=indiv_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    else:
        return render(request, 'individual/individual_home.html', {
            'project': project,
            'individual': individual,
        })


