from django.contrib.auth.decorators import login_required
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.conf import settings
from xbrowse_server.server_utils import JSONResponse
from xbrowse_server.reports.utilities import fetch_project_single_individual_data
import hashlib

@login_required
@log_request('matchmaker_add')
def add_individual(request, project_id, individual_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        family_data,variant_data,phenotype_entry_counts,family_statuses = fetch_project_single_individual_data(project_id, individual_id)
    
    #make a unique hash to represent individual in MME for MME_ID
    h = hashlib.md5()
    h.update(individual_id)
    id=h.hexdigest()
    label=id #using ID as label
    #map to put into mongo
    map={"individual_id":individual_id,
         "mme_id":id}
    
    #species
    species="NCBITaxon:9606"

    #contact (this should be set in settings
    contact={
             "name":"Harindra Arachchi",
             "institution" : "Joint Center for Mendelian Disease at the Broad Institute",
             "href" : "http://www.broadinstitute.org/"
             }
    
    #for testing only, should return a success/fail message
    return JSONResponse({"patient":
                         {
                          "id":id,
                          "species":species,
                          "label":label,
                          "contact":contact
                          }
        })
