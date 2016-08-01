from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from xbrowse_server.server_utils import JSONResponse
from xbrowse_server.decorators import log_request
#from utilities import fetch_project_individuals_data
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.shortcuts import render



@csrf_exempt
@login_required
@log_request('project_report')
def project_report(request, project_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this report
    '''
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    return render(request, 'reports/project_report.html', {
        'project': project,
    })


    