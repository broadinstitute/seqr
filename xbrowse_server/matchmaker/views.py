from django.contrib.auth.decorators import login_required
from xbrowse_server.decorators import log_request
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.conf import settings
from xbrowse_server.server_utils import JSONResponse
from xbrowse_server.phenotips.reporting_utilities import get_phenotypes_entered_for_individual
from xbrowse_server.reports.utilities import fetch_project_individuals_data
import hashlib
import datetime

@login_required
@log_request('matchmaker_add')
def add_individual(request, project_id, individual_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        phenotypes_entered = get_phenotypes_entered_for_individual(individual_id,project_id)
        
    #make a unique hash to represent individual in MME for MME_ID
    h = hashlib.md5()
    h.update(individual_id)
    id=h.hexdigest()
    label=id #using ID as label
    #map to put into mongo
    id_map={"generated_on": datetime.datetime.now(),
         "project_id":project_id,
         "individual_id":individual_id,
         "mme_id":id}
    #settings.SEQR_ID_TO_MME_ID_MAP.insert(id_map)
    
    #species (only human for now) till seqr starts tracking species
    species="NCBITaxon:9606"

    #contact (this should be set in settings
    contact={
             "name":"Harindra Arachchi",
             "institution" : "Joint Center for Mendelian Disease at the Broad Institute",
             "href" : "mailto:harindra@broadinstitute.org"
             }
    
    #need to eventually support "FEMALE"|"MALE"|"OTHER"|"MIXED_SAMPLE"|"NOT_APPLICABLE",
    #as of now PhenoTips only has M/F
    sex="FEMALE"
    if "M" == phenotypes_entered['sex']:
        sex="MALE"
        
    #features section
    features=[]
    for f in phenotypes_entered['features']:
        features.append({
                        "id":f['id'],
                        "observed":f['observed']
                        }
                        )
        
    #genomicFeatures section
    genomic_features=[]
    family_data,variant_data,_,_ = fetch_project_individuals_data(project_id)
    for f in family_data:
        reference_bases = f['ref']
        alternate_bases = f['alt']
        reference_name = f['chr'].replace('chr','')
        start = f['pos']
        end = str(int(start) + len(alternate_bases))
        #now we have more than 1 gene associated to these VAR postions,
        #so we will associate that information to each gene symbol
        for gene_id,values in f['extras']['genes'].iteritems():
            genomic_feature = {}
            genomic_feature['gene'] ={"id": values['symbol'] }
            genomic_feature['variant']={
                                        'assembly':settings.GENOME_ASSEMBLY_NAME,
                                        'referenceBases':reference_bases,
                                        'alternateBases':alternate_bases,
                                        'start':start,
                                        'end':end,
                                        'referenceName':reference_name
                                        }
            genomic_features.append(genomic_feature)        
        
        print genomic_feature
    
    #for testing only, should return a success/fail message
    return JSONResponse({"patient":
                         {
                          "id":id,
                          "species":species,
                          "label":label,
                          "contact":contact,
                          "features":features,
                          "sex":sex,
                          "genomicFeatures":genomic_features
                          }
        })
