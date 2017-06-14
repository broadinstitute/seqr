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
from django.contrib.admin.views.decorators import staff_member_required
 
@csrf_exempt
@login_required
@log_request('matchmaker_landing_page')
def matchmaker_add_page(request, project_id,family_id,individual_id):
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
    return render(request, 'matchmaker/matchmaker_search_page.html',{})


@csrf_exempt
@log_request('matchmaker_disclaimer_page')
def matchmaker_disclaimer_page(request):
    '''
    Serves page with disclaimer message
    Notes: 
        Login is NOT required, this will be a general access page
    '''
    return render(request, 'matchmaker/matchmaker_disclaimer_page.html', {})


@login_required
@staff_member_required
def matchbox_id_info(request):
    '''
    Shows information about this matchbox_id such as the sample_id in seqr
    Notes: 
        User HAS TO BE staff to access this page
    '''
    return render(request, 'matchmaker/matchbox_id_info.html', {})


@login_required
@staff_member_required
def matchbox_dashboard(request):
    '''
    Dashboard on current matchbox status
    Notes: 
        User HAS TO BE staff to access this page
    '''
    return render(request, 'matchmaker/matchbox_dashboard.html', {})

