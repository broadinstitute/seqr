from django.contrib.auth.decorators import login_required
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.conf import settings
from xbrowse_server.server_utils import JSONResponse
import requests
import json
from xbrowse_server.matchmaker.utilities import get_all_clinical_data_for_individual


"""DEPRACATED
#@login_required
#@log_request('matchmaker_add')
def add_individual(request, project_id, individual_id):
    
    #Adds an individual data to local MME database for sharing and matching
    #Args:
    #    project_id: project this individual belongs to
    #    individual_id: the individual to be added
    #Returns:
    #    A status code and the patient data that was persisted
    #
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:    
        patient = get_all_clinical_data_for_individual(project_id,individual_id)
        #insert patient into MME
        headers={
               'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
               'Accept': settings.MME_NODE_ACCEPT_HEADER,
               'Content-Type': settings.MME_CONTENT_TYPE_HEADER
             }
        result = requests.post(url=settings.MME_ADD_INDIVIDUAL_URL,
                           headers=headers,
                           data=json.dumps(patient))
        #for testing only, should return a success/fail message
        return JSONResponse({"status_code":result.status_code,
                         "exported_patient":patient})
"""   
    
@login_required
@log_request('matchmaker_individual_match_locally')
def match_individual_locally(request,project_id,family_id):
    """
    Looks for matches for the given individual ONLY in the local database
    Args:
        individual_id: an individual ID
        project_id: project this individual belongs to
    Returns:
        Status code and results
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        id_map,patient = get_all_clinical_data_for_individual(project_id,family_id)
        headers={
               'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
               'Accept': settings.MME_NODE_ACCEPT_HEADER,
               'Content-Type': settings.MME_CONTENT_TYPE_HEADER
             }
        result = requests.post(url=settings.MME_LOCAL_MATCH_URL,
                           headers=headers,
                           data=json.dumps(patient))

        if 200 == result.status_code:
            if 0 ==settings.SEQR_ID_TO_MME_ID_MAP.find({"individual_id":individual_id,"project_id":project_id}).count():
                settings.SEQR_ID_TO_MME_ID_MAP.insert(id_map)
                inserted_message="Successfully inserted into the Broad Institute matchmaker exchange system."
            else:
                inserted_message="Individual already exists in the Broad Institute matchmaker exchange system, not inserting."
        else:
            inserted_message="Sorry, there was a technical error inserting this individual into the Broad Institute matchmaker exchange system, please contact seqr help"
        return JSONResponse({
                             "insertion_message":inserted_message,
                             "match_result":result.json()
                             })
        
