from django.contrib.auth.decorators import login_required
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.conf import settings
from xbrowse_server.server_utils import JSONResponse
import requests
import json
from xbrowse_server.matchmaker.utilities import get_all_clinical_data_for_family
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
 
 
@csrf_exempt
@login_required
@log_request('matchmaker_landing_page')
def matchmaker_add_page(request, project_id,family_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this report
    '''
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    return render(request, 'matchmaker/matchmaker_add_page.html', {
        'project': project,
    })
 
 
@csrf_exempt
@login_required
@log_request('matchmaker_search_page')
def matchmaker_search_page(request, project_id,family_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this report AND they have to have submitted to MME first
    '''
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    return render(request, 'matchmaker/matchmaker_search_page.html', {})


    

