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
    
    return render(request, 'matchmaker/matchmaker_landing_page.html', {
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
 
    
    
    
    
    
#---------------------DEPRACATED
"""
#@login_required
#@csrf_exempt
#@log_request('matchmaker_individual_match')
def match_individual(request,project_id):

    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results
    
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:
        patient_data = json.loads(request.POST.get("patient_data","wasn't able to parse POST!"))
        headers={
               'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
               'Accept': settings.MME_NODE_ACCEPT_HEADER,
               'Content-Type': settings.MME_CONTENT_TYPE_HEADER
             }
        results={}
        #first look in the local MME database
        internal_result = requests.post(url=settings.MME_LOCAL_MATCH_URL,
                               headers=headers,
                               data=patient_data
                               )
        results['local_results']={"result":internal_result.json(), 
                                  "status_code":str(internal_result.status_code)
                          }
        #then look at other nodes COMMENTED FOR TESTING
        #extnl_result = requests.post(url=settings.MME_EXTERNAL_MATCH_URL,
        #                       headers=headers,
        #                       data=patient_data
        #                       )
        #results['external_results']={"result":extnl_result.json(),
        #                             "status_code":str(extnl_result.status_code)
        #                     }
        return JSONResponse({
                             "match_results":results
                             })
"""


    

