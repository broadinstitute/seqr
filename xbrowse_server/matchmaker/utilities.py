from xbrowse_server.phenotips.reporting_utilities import get_phenotypes_entered_for_individual
import hashlib
import datetime
from django.conf import settings
from xbrowse_server.base.models import Individual
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project, Family
from xbrowse_server.base.models import ProjectTag, VariantTag
from xbrowse_server.mall import get_datastore
import time
from xbrowse_server.mall import get_reference

def get_all_clinical_data_for_family(project_id,family_id):
    """
        Gets phenotype and genotype data for this individual
        Args:
            family_id: id of family
        Returns:
            A JSON object as per MME spec of a patient
    """
    project = get_object_or_404(Project, project_id=project_id)

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
    variants=[]
    project_tags = ProjectTag.objects.filter(project__project_id=project_id)
    for project_tag in project_tags:
        variant_tags = VariantTag.objects.filter(project_tag=project_tag)
        for variant_tag in variant_tags:    
            if family_id == variant_tag.toJSON()['family']:
                variant = get_datastore(project.project_id).get_single_variant(
                        project.project_id,
                        variant_tag.toJSON()['family'],
                        variant_tag.xpos,
                        variant_tag.ref,
                        variant_tag.alt,
                )
                if variant is None:
                    raise ValueError("Variant no longer called in this family (did the callset version change?)")
                variants.append({"variant":variant.toJSON(),
                                 "tag":project_tag.title,
                                 "family":variant_tag.family.toJSON(),
                                 "tag_name":variant_tag.toJSON()['tag']
                                 })
    #start compiling a matchmaker-esque data structure to send back
    genomic_features=[]
    for variant in variants:
        start = variant['variant']['pos']
        reference_bases = variant['variant']['ref']
        alternate_bases = variant['variant']['alt']
        end = int(variant['variant']['pos_end']) #int and long are unified in python
        reference_name = variant['variant']['chr'].replace('chr','')        
        #now we have more than 1 gene associated to these VAR postions,
        #so we will associate that information to each gene symbol
        for i,gene_id in enumerate(variant['variant']['gene_ids']):
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
            
            gene_symbol=""
            if gene_id != "":
                gene = get_reference().get_gene(gene_id)
                gene_symbol = gene['symbol']

            genomic_feature['auxiliary']={
                                          "tag_name":variant['tag_name'],
                                          "gene_symbol":gene_symbol
                                          }
            genomic_features.append(genomic_feature) 

    #all affected patients
    affected_patients=[]
    detailed_id_map=[]
    id_map={}
    
    #--find individuals in this family
    family = Family.objects.get(project=project, family_id=family_id)
    for indiv in family.get_individuals():
        if indiv.affected_status_display() == 'Affected':
            phenotypes_entered = get_phenotypes_entered_for_individual(project_id,indiv.phenotips_id)
            #need to eventually support "FEMALE"|"MALE"|"OTHER"|"MIXED_SAMPLE"|"NOT_APPLICABLE",
            #as of now PhenoTips only has M/F
            sex="FEMALE"
            if "M" == indiv.gender:
                sex="MALE"
            features=[]
            if phenotypes_entered.has_key('features'):
                #as of now non-standard features ('nonstandard_features') without HPO
                #terms cannot be sent to MME
                for f in phenotypes_entered['features']:
                    features.append({
                        "id":f['id'],
                        "observed":f['observed']})
            #make a unique hash to represent individual in MME for MME_ID
            h = hashlib.md5()
            h.update(indiv.indiv_id)
            id=h.hexdigest()
            label=id #using ID as label
            id_map[id]=indiv.indiv_id
            #add new patient to affected patients
            affected_patients.append({
                                      "patient":
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
            time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S')
            detailed_id_map.append({"generated_on": time_stamp,
                 "project_id":project_id,
                 "family_id":family_id,
                 "individual_id":indiv.indiv_id,
                 "mme_id":id,
                 "individuals_used_for_phenotypes":affected_patients})

    return detailed_id_map,affected_patients,id_map
            
    
    

def is_a_valid_patient_structure(patient_struct):
    """
    Checks to see if the input patient data structure has all the
    data/fields required by the MME
    Args:
        patient structure
    Returns:
        True if valid
    """
    submission_validity={"status":True, "reason":""}
    #check if all gene IDs are present
    for gf in patient_struct['genomicFeatures']:
        if gf['gene']['id'] == "":
            submission_validity['status']=False
            submission_validity['reason']="Gene ID is required, and is missing in one of the genotypes. Please refine your submission"
    return submission_validity
    