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
def matchmaker_landing_page(request, project_id,family_id):
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
 
 
    
@login_required
@csrf_exempt
@log_request('matchmaker_individual_match')
def match_individual(request,project_id):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
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
        



    
@login_required
@log_request('matchmaker_individual_add')
def add_individual(request,project_id,family_id):
    """
    Adds given individual to the local database
    Args:
        individual_id: an individual ID
        project_id: project this individual belongs to
    Returns:
        Status code
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        id_maps,affected_patients,id_map = get_all_clinical_data_for_family(project_id,family_id)
        headers={
               'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
               'Accept': settings.MME_NODE_ACCEPT_HEADER,
               'Content-Type': settings.MME_CONTENT_TYPE_HEADER
             }
        submission_statuses=[]
        for i,affected_patient in enumerate(affected_patients):
            result = requests.post(url=settings.MME_ADD_INDIVIDUAL_URL,
                           headers=headers,
                           data=json.dumps(affected_patient))
            submission_statuses.append({
                                        'http_result':result.json(),
                                        'status_code':str(result.status_code),
                                        'submitted_data':json.dumps(affected_patient),
                                        'id_map':{'local_id':id_map[affected_patient['patient']['id']],
                                                  'obfuscated_id':affected_patient['patient']['id']
                                                  }
                                        }
                                       )
            #persist the map too
            if 200 == result.status_code:
                settings.SEQR_ID_TO_MME_ID_MAP.insert(id_maps[i])
        return JSONResponse({
                             "submission_details":submission_statuses
                             })
        
