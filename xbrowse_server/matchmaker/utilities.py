from xbrowse_server.phenotips.reporting_utilities import get_phenotypes_entered_for_individual
import hashlib
import datetime
from django.conf import settings
from xbrowse_server.reports.utilities import fetch_project_individuals_data

def get_all_clinical_data_for_individual(project_id,family_id):
    """
        Gets phenotype and genotype data for this individual
        Args:
            family_id: id of family
        Returns:
            A JSON object as per MME spec of a patient
    """
    
    #species (only human for now) till seqr starts tracking species
    species="NCBITaxon:9606"

    #contact (this should be set in settings
    contact={
             "name":settings.MME_CONTACT_NAME,
             "institution" : settings.MME_CONTACT_INSTITUTION,
             "href" : settings.MME_CONTACT_HREF
             }
        
    #genomicFeatures section
    genomic_features=[]
    family_data,variant_data,_,_ = fetch_project_individuals_data(project_id)
    for f in family_data:
        reference_bases = f['ref']
        alternate_bases = f['alt']
        reference_name = f['chr'].replace('chr','')
        start = int(f['pos'])
        end = int(start) + len(alternate_bases)
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
            
    #get a list of affected individuals
    affected_individuals=[]
    for v in variant_data:
        if family_id == variant_data[v]['family_id']:
            for indiv in variant_data[v]['individuals']:
                if indiv['affected']=='A':
                    affected_individuals.append(indiv['indiv_id'])
            
    #add phenotypes of ALL AFFECTED INDIVIDUALS  
    features=[]
    for individual_id in affected_individuals:
        phenotypes_entered = get_phenotypes_entered_for_individual(individual_id,project_id)
        
        #need to eventually support "FEMALE"|"MALE"|"OTHER"|"MIXED_SAMPLE"|"NOT_APPLICABLE",
        #as of now PhenoTips only has M/F
        sex="FEMALE"
        if "M" == phenotypes_entered['sex']:
            sex="MALE"
            
        #since we are using a union of phenotypes, this can be M/F so leaving it out,
        sex=""
        for f in phenotypes_entered['features']:
            features.append({
                            "id":f['id'],
                            "observed":f['observed']
                            }
                            )
    #make a unique hash to represent individual in MME for MME_ID
    h = hashlib.md5()
    h.update(family_id)
    id=h.hexdigest()
    label=id #using ID as label
    #map to put into mongo
    id_map={"generated_on": datetime.datetime.now(),
         "project_id":project_id,
         "family_id":family_id,
         "mme_id":id,
         "individuals_used_for_phenotypes":affected_individuals}
    
    return id_map,{"patient":
                         {
                          "id":id,
                          "species":species,
                          "label":label,
                          "contact":contact,
                          "features":features,
                          "sex":sex,
                          "genomicFeatures":genomic_features
                          }
            }
    
    
    
    
def find_affected_individuals_in_family(family_id,project_id):
    """
    Finds all affected individuals in this family
    Args:
        family_id: Id of family (str)
        project_id: Id of project (str)
    Returns:
    A list of individual IDs
    Ex: ['HG00731','HG00732']
    """
    #not needed?
    pass
    
    