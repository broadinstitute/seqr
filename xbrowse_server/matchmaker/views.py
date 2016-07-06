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

 
    
@login_required
@log_request('matchmaker_individual_match_locally')
def match_individual(request,project_id,family_id):
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
        id_maps,affected_patients,id_map = get_all_clinical_data_for_family(project_id,family_id)
        '''
        return JSONResponse({
                             "results":affected_patients,
                             })
        '''
        headers={
               'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
               'Accept': settings.MME_NODE_ACCEPT_HEADER,
               'Content-Type': settings.MME_CONTENT_TYPE_HEADER
             }
        submission_statuses=[]
        for affected_patient in affected_patients:
            result = requests.post(url=settings.MME_LOCAL_MATCH_URL,
                           headers=headers,
                           data=json.dumps(affected_patient))
            submission_statuses.append({
                                        'status_code':result.status_code,
                                        'submitted_data':affected_patient,
                                        'id_map':{'local_id':id_map[affected_patient['patient']['id']],
                                                  'obfuscated_id':affected_patient['patient']['id']
                                                  }
                                        }
                                       )
        inserted_message=''
        for submission_status in submission_statuses: 
            print submission_status
            if 200 == result.status_code:
                if 0 ==settings.SEQR_ID_TO_MME_ID_MAP.find({"family_id":family_id,"project_id":project_id}).count():
                    settings.SEQR_ID_TO_MME_ID_MAP.insert(id_maps)
                    inserted_message="Successfully inserted into the Broad Institute matchmaker exchange system."
                else:
                    inserted_message="Family already exists in the Broad Institute matchmaker exchange system, not inserting."
            else:
                inserted_message="Sorry, there was a technical error inserting this individual into the Broad Institute matchmaker exchange system, please contact seqr help"
        
        
        return JSONResponse({
                             "insertion_message":inserted_message,
                             "match_result":result.json()
                             })
        
