from django.contrib.auth.decorators import login_required

from settings import LOGIN_URL
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project, Family
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
    family = get_object_or_404(Family, project=project, family_id=family_id)
    
    return render(request, 'matchmaker/matchmaker_add_page.html', {
        'project': project,
        'new_page_url': '/project/{0}/family_page/{1}/matchmaker_exchange'.format(
            family.seqr_family.project.guid, family.seqr_family.guid) if family.seqr_family else None,
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
    family = get_object_or_404(Family, project=project, family_id=family_id)
    return render(request, 'matchmaker/matchmaker_search_page.html',{
        'new_page_url': '/project/{0}/family_page/{1}/matchmaker_exchange'.format(
            family.seqr_family.project.guid, family.seqr_family.guid) if family.seqr_family else None,
    })


@csrf_exempt
@log_request('matchmaker_disclaimer_page')
def matchmaker_disclaimer_page(request):
    '''
    Serves page with disclaimer message
    Notes: 
        Login is NOT required, this will be a general access page
    '''
    return render(request, 'matchmaker/matchmaker_disclaimer_page.html', {})


@staff_member_required(login_url=LOGIN_URL)
def matchbox_id_info(request):
    '''
    Shows information about this matchbox_id such as the sample_id in seqr
    Notes: 
        User HAS TO BE staff to access this page
    '''
    return render(request, 'matchmaker/matchbox_id_info.html', {'new_page_url': '/staff/matchmaker'})


@staff_member_required(login_url=LOGIN_URL)
def matchbox_dashboard(request):
    '''
    Dashboard on current matchbox status
    Notes: 
        User HAS TO BE staff to access this page
    '''
    return render(request, 'matchmaker/matchbox_dashboard.html', {'new_page_url': '/staff/matchmaker'})


@log_request('matchmaker_info_page')
@csrf_exempt
def matchbox_info_page(request):
    '''
    Serves page with some basic info matchbox at Broad
    Notes: 
        Login is NOT required, this will be a general access page
    '''
    return render(request, 'matchmaker/matchbox_info_page.html', {})
