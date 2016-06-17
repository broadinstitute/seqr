from xbrowse_server.phenotips.reporting_utilities import get_phenotypes_entered_for_individual
import hashlib
import datetime
from django.conf import settings
from xbrowse_server.reports.utilities import fetch_project_individuals_data
from xbrowse_server.base.models import Individual
def get_all_clinical_data_for_family(project_id,family_id):
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
    #family_data,variant_data,_,_ = fetch_project_individuals_data(project_id)
    variants,phenotype_entry_counts = fetch_project_individuals_data(project_id)

    for variant in variants:
        start = variant['xpos']
        reference_bases = variant['ref']
        alternate_bases = variant['alt']
        end = variant['pos_end']
        reference_name = variant['chr'].replace('chr','')
        
        #now we have more than 1 gene associated to these VAR postions,
        #so we will associate that information to each gene symbol
        genomic_features=[]
        for i,gene_id in enumerate(variant['gene_ids']):
            genomic_feature = {}
            genomic_feature['gene'] ={"id": gene_id }
            genomic_feature['variant']={
                                        'assembly':settings.GENOME_ASSEMBLY_NAME,
                                        'referenceBases':reference_bases,
                                        'alternateBases':alternate_bases,
                                        'start':start,
                                        'end':end,
                                        'referenceName':reference_name
                                        }
            genomic_features.append(genomic_feature) 
        
        
        #for k,v in variant.iteritems(): 
        #    print (k+ '   ' + str(v)  + '\n')
        #print('--------------------\n')
    
    #for f in family_data:
    #    reference_bases = f['ref']
    #    alternate_bases = f['alt']
    #    reference_name = f['chr'].replace('chr','')
    #    start = int(f['pos'])
    #    end = int(start) + len(alternate_bases)
    #    #now we have more than 1 gene associated to these VAR postions,
    #    #so we will associate that information to each gene symbol
    #    for gene_id,values in f['extras']['genes'].iteritems():
    #        genomic_feature = {}
    #        genomic_feature['gene'] ={"id": values['symbol'] }
    #        genomic_feature['variant']={
    #                                    'assembly':settings.GENOME_ASSEMBLY_NAME,
    #                                    'referenceBases':reference_bases,
    #                                    'alternateBases':alternate_bases,
    #                                    'start':start,
    #                                    'end':end,
    #                                    'referenceName':reference_name
    #                                    }
    #        genomic_features.append(genomic_feature)   


    #all affected patients
    affected_patients=[]
    id_maps=[]
  
    for variant in variants:
        print '+++++++'
        #for i in variant['annotation'].keys():
        #    print i,variant['annotation'][i]
        for genotype,details in variant['genotypes'].iteritems():
            individual = Individual.objects.get(project__project_id=project_id, indiv_id=genotype)
            for ind in individual.family.get_individuals():
                print ind.affected
                print ind.indiv_id
        print '+++++++'
    
    
    #find phenotypes for each affected individual
    for v in variant_data:
        if family_id == variant_data[v]['family_id']:
            for indiv in variant_data[v]['individuals']:
                if indiv['affected']=='A':
                    individual_id = indiv['indiv_id']
                    phenotypes_entered = get_phenotypes_entered_for_individual(individual_id,project_id)
        
                    #need to eventually support "FEMALE"|"MALE"|"OTHER"|"MIXED_SAMPLE"|"NOT_APPLICABLE",
                    #as of now PhenoTips only has M/F
                    sex="FEMALE"
                    if "M" == indiv['gender']:
                        sex="MALE"
                    features=[]
                    for f in phenotypes_entered['features']:
                        features.append({
                            "id":f['id'],
                            "observed":f['observed']
                            }
                            )
                    #make a unique hash to represent individual in MME for MME_ID
                    h = hashlib.md5()
                    h.update(individual_id)
                    id=h.hexdigest()
                    label=id #using ID as label
                    #add new patient to affected patients
                    affected_patients.append({"patient":
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
                    #map to put into mongo
                    id_maps.append({"generated_on": datetime.datetime.now(),
                         "project_id":project_id,
                         "family_id":family_id,
                         "individual_id":individual_id,
                         "mme_id":id,
                         "individuals_used_for_phenotypes":affected_patients})

    return id_maps,affected_patients
            
    
    

    