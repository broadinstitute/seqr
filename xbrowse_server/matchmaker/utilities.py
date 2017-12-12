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
import json
from slacker import Slacker
from collections import defaultdict, namedtuple
from xbrowse_server.gene_lists.models import GeneList
from tqdm import tqdm
from reference_data.models import HumanPhenotypeOntology
import logging
from django.core.exceptions import ObjectDoesNotExist
from seqr.models import Project as SeqrProject
from seqr.models import Dataset as Dataset
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger()

def get_all_clinical_data_for_family(project_id,family_id,indiv_id):
    """
        Gets phenotype and genotype data for this individual
        Args:
            family_id: id of family
        Returns:
            A JSON object as per MME spec of a patient
    """
    project = get_object_or_404(Project, project_id=project_id)
    
    #get contact information if available
    seqr_project = project.seqr_project 
    #Ideally these (the default Sam, and matchmaker@broad) should be set at project creation   
    seqr_project.is_mme_enabled=True 
    seqr_project.mme_primary_data_owner=settings.MME_CONTACT_NAME
    seqr_project.mme_contact_url=settings.MME_CONTACT_HREF
    seqr_project.save();

    #species (only human for now) till seqr starts tracking species
    species="NCBITaxon:9606"
    
    contact={
             "name":seqr_project.mme_primary_data_owner,
             "institution" : settings.MME_CONTACT_INSTITUTION,
             "href" : seqr_project.mme_contact_url
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
                    logging.info("Variant no longer called in this family (did the callset version change?)")
                    continue
                variants.append({"variant":variant.toJSON(),
                                 "tag":project_tag.title,
                                 "family":variant_tag.family.toJSON(),
                                 "tag_name":variant_tag.toJSON()['tag']
                                 })
                
    current_genome_assembly = find_genome_assembly(seqr_project)
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
                                        'assembly':current_genome_assembly,
                                        'referenceBases':reference_bases,
                                        'alternateBases':alternate_bases,
                                        'start':start,
                                        'end':end,
                                        'referenceName':reference_name
                                        }
            genomic_feature['zygosity'] = variant['variant']['genotypes'][indiv_id]['num_alt']
            gene_symbol=""
            if gene_id != "":
                gene = get_reference().get_gene(gene_id)
                gene_symbol = gene['symbol']

            genomic_feature['auxiliary']={
                                          "tag_name":variant['tag_name'],
                                          "gene_symbol":gene_symbol
                                          }
            genomic_features.append(genomic_feature) 
    
    #Find phenotype information
    indiv = Individual.objects.get(indiv_id=indiv_id,project=project)
    phenotypes_entered = get_phenotypes_entered_for_individual(project_id,indiv.phenotips_id)
    #need to eventually support "FEMALE"|"MALE"|"OTHER"|"MIXED_SAMPLE"|"NOT_APPLICABLE",
    #as of now PhenoTips only has M/F
    sex="NOT_APPLICABLE"
    if "M" == indiv.gender:
        sex="MALE"
    if "F" == indiv.gender:
        sex="FEMALE"
    features=[]
    if phenotypes_entered.has_key('features'):
        #as of now non-standard features ('nonstandard_features') without HPO
        #terms cannot be sent to MME
        for f in phenotypes_entered['features']:
            features.append({
                "id":f['id'],
                "observed":f['observed'],
                "label":f['label']})
    
    id=indiv.indiv_id
    label=indiv.indiv_id

    #add new patient to affected patients
    affected_patient={"id":id,
                      "species":species,
                      "label":label,
                      "contact":contact,
                      "features":features,
                      "sex":sex,
                      "genomicFeatures":genomic_features
                      }
                            
    #map to put into mongo
    time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S')
    detailed_id_map={"generated_on": time_stamp,
         "project_id":project_id,
         "family_id":family_id,
         "individual_id":indiv.indiv_id,
         "mme_id":id,
         "individuals_used_for_phenotypes":affected_patient}
    return detailed_id_map,affected_patient
            
            
def find_genome_assembly(project):
    """
    Find the genome assembly of this individual
    Args:
        project: This is a seqr.project object reprenting the project
    Returns:
    The genome assembly version
    """
    datasets =  Dataset.objects.filter(analysis_type=Dataset.ANALYSIS_TYPE_VARIANT_CALLS, project=project)
    if datasets and datasets[0].genome_version:
        return 'GRCh' + datasets[0].genome_version
    return 'GRCh37'

def is_a_valid_patient_structure(patient_struct):
    """
    Checks to see if the input patient data structure has all the
    data/fields required by the MME
    Args:
        patient structure
    Returns:
        True if valid
    TODO:
        This function needs improvement and checks on field naming and other required values.
    """
    submission_validity={"status":True, "reason":""}
    #check if all gene IDs are present
    for gf in patient_struct['genomicFeatures']:
        if gf['gene']['id'] == "":
            submission_validity['status']=False
            submission_validity['reason']="Gene ID is required, and is missing in one of the genotypes. Please refine your submission"
    return submission_validity


def generate_slack_notification_for_incoming_match(response_from_matchbox,incoming_request,incoming_external_request_patient):
    """
    Generate a SLACK notifcation to say that a VALID match request came in and the following
    results were sent back. If Slack is not supported, a message is not sent, but details persisted.
    Args:
        The response from matchbox
        The request that came in
    Returns:
        The generated and sent notification
    """
    results_from_matchbox = response_from_matchbox.json()['results']
    incoming_patient_as_json = json.loads(incoming_external_request_patient.strip())
    
    institution = incoming_patient_as_json['patient']['contact'].get('institution','(institution name not given)')
    message = 'Hey folks, this match request came in from ' + institution  + ' today (' + time.strftime('%d, %b %Y')  + ').' 
    message += ' Their contact URL was: ' + incoming_patient_as_json['patient']['contact'].get('href','(invalid URL!') + '. '
    if len(results_from_matchbox) > 0:
        if incoming_patient_as_json['patient'].has_key('genomicFeatures'):
            message += 'The following gene(s), '
            for i,genotype in enumerate(incoming_patient_as_json['patient']['genomicFeatures']):
                gene_id = genotype['gene']['id']
                #try to find the gene symbol and add to notification
                gene_symbol=gene_id
                if gene_id != "" and 'ENS'==gene_id[0:3]:
                    gene = get_reference().get_gene(gene_id)
                    gene_symbol = gene.get('symbol','(sorry, HGNC symbol not found)')
                    
                message += gene_id
                if 'ENS'==gene_id[0:3]:
                    message += " ("
                    message += gene_symbol
                    message += ")"
                if i<len(incoming_patient_as_json['patient']['genomicFeatures'])-1:
                    message += ', '
                    
            message += ' came-in with this request.\n\n'
        
        message += '*We found matches to these genes in matchbox! The matches are*,\n '
        for result in results_from_matchbox:
            seqr_id_maps = settings.SEQR_ID_TO_MME_ID_MAP.find({"submitted_data.patient.id":result['patient']['id']}).sort('insertion_date',-1).limit(1)
            for seqr_id_map in seqr_id_maps:
                message += ' seqr ID ' + seqr_id_map['seqr_id'] 
                message += ' from project ' +    seqr_id_map['project_id'] 
                message += ' in family ' +  seqr_id_map['family_id'] 
                message += ', inserted into matchbox on ' + seqr_id_map['insertion_date'].strftime('%d, %b %Y')
                message += '. '
                message += settings.SEQR_HOSTNAME_FOR_SLACK_POST + '/' + seqr_id_map['project_id'] + '/family' +  seqr_id_map['family_id'] 
                message += '\n\n'
            settings.MME_EXTERNAL_MATCH_REQUEST_LOG.insert({
                                                        'seqr_id':seqr_id_map['seqr_id'],
                                                        'project_id':seqr_id_map['project_id'],
                                                        'family_id': seqr_id_map['family_id'],
                                                        'mme_insertion_date_of_data':seqr_id_map['insertion_date'],
                                                        'host_name':incoming_request.get_host(),
                                                        'query_patient':incoming_patient_as_json
                                                        }) 
        message += 'These matches were sent back today (' + time.strftime('%d, %b %Y')  + ').'
        if settings.SLACK_TOKEN is not None:
            post_in_slack(message,settings.MME_SLACK_MATCH_NOTIFICATION_CHANNEL)
    else:
        message += " We didn't find any individuals in matchbox that matched that query well, *so no results were sent back*. "
        if settings.SLACK_TOKEN is not None:
            post_in_slack(message,settings.MME_SLACK_EVENT_NOTIFICATION_CHANNEL)        
    
    
def generate_slack_notification_for_seqr_match(response_from_matchbox,project_id,seqr_id):
    """
    Generate a SLACK notifcation to say that a match happened initiated from a seqr user.
    """
    message = '\n\nA search from a seqr user from project ' + project_id + ' individual ' + seqr_id + ' originated match(es):'
    message += '\n'
    for result_origin,result in response_from_matchbox.iteritems():
        status_code=response_from_matchbox[result_origin]['status_code']
        results=response_from_matchbox[result_origin]['result']['results']
        
        for result in results:
            score=result['score']
            patient=result['patient']
            gene_ids=[]
            if patient.has_key('genomicFeatures'):
                for gene in patient['genomicFeatures']:
                    gene_ids.append(gene['gene']['id'])
            phenotypes=[]
            if patient.has_key('features'):
                for feature in patient['features']:
                    phenotypes.append(feature['id']) 
            if len(gene_ids)>0:
                message += ' with genes ' + ' '.join(gene_ids)
            if len(phenotypes)>0:
                message += ' and phenotypes ' + ' '.join(phenotypes)
            message += ' from institution "' + patient['contact'].get('institution','(none given)') + '" and contact "' + patient['contact'].get('name','(none given)') + '"'
            message += '. '
            message += settings.SEQR_HOSTNAME_FOR_SLACK_POST + '/' + project_id
            message += '\n\n'
            post_in_slack(message,'matchmaker_seqr_match')

    
def post_in_slack(message,channel):
    """
    Posts to Slack
    Args:
        The message to post
        The channel to post to
    Returns:
        The submission result state details from Slack
    """
    slack = Slacker(settings.SLACK_TOKEN)
    response = slack.chat.post_message(channel, message, as_user=False, icon_emoji=":beaker:", username="Beaker (engineering-minion)")
    return response.raw
            
            
            
def find_latest_family_member_submissions(submission_records):
    """
    Given a list of submissions, isolate the latest 2 submissions from the family
    """
    individual ={}
    for submission in submission_records:  
        if individual.has_key(submission['seqr_id']):
             if submission['insertion_date'] > individual[submission['seqr_id']]['insertion_date']:
                 individual[submission['seqr_id']]=submission
        else:
            individual[submission['seqr_id']]=submission 
    return individual


def convert_matchbox_id_to_seqr_id(matchbox_id):
    """
    Given a matchbox ID returns a seqr ID
    Args:
        A matchbox ID
    Returns:
        A seqr ID
    """
    try:
        patient=settings.SEQR_ID_TO_MME_ID_MAP.find_one({'submitted_data.patient.id':matchbox_id})
        return patient['seqr_id']
    except:
        raise
    

def gather_all_annotated_genes_in_seqr():
    """
    Finds all genes mentioned in seqr
    Args:
        No arguments
    Returns
        A default dict where the key is a named tuple of gene HGNC ID and ensemble ID and the values are projects where
        this gene appears
    """
    #genomicFeatures section
    all_gene_lists = defaultdict(set)
    gene_to_gene_lists = defaultdict(set)
    for gene_list in GeneList.objects.all():
        all_gene_lists[gene_list.name] = set(g.gene_id for g in gene_list.genelistitem_set.all())
        for g in gene_list.genelistitem_set.all():
            gene_to_gene_lists[g.gene_id].add(gene_list.name)

    gene_to_projects = defaultdict(set)

    Key = namedtuple('Key', 'gene_id, gene_name')
    project_ids = defaultdict(int)
    for variant_tag in tqdm(VariantTag.objects.filter(), unit=' variants'):
        project_tag = variant_tag.project_tag
        project_id = project_tag.project.project_id
        project_ids[project_id] += 1
        tag_name = project_tag.tag.lower()

        variant = get_datastore(project_id).get_single_variant(
            project_id,
            variant_tag.family.family_id,
            variant_tag.xpos,
            variant_tag.ref,
            variant_tag.alt,
        )
        if variant is None:
            continue

        if variant.gene_ids is not None:
            for gene_id in variant.gene_ids:
                gene_name = get_reference().get_gene_symbol(gene_id)
                key = Key._make([gene_id, gene_name])
                gene_to_projects[key].add(project_id.lower())

    return gene_to_projects


def find_projects_with_families_in_matchbox():
    """
    Find projects that have families in matchbox
    Returns:
        A dictionary with the key being a project name and the value being a dictionary with the
        key being a family name and the value being the insertion date of that family into matchbox
    """
    all_submissions = settings.SEQR_ID_TO_MME_ID_MAP.find({})
    most_recent_submission={}
    for submission in all_submissions:
        if most_recent_submission.has_key(submission['project_id']):
            if most_recent_submission[submission['project_id']].has_key(submission['family_id']):
                if submission['insertion_date'] > most_recent_submission[submission['project_id']][submission['family_id']]:
                    most_recent_submission[submission['project_id']][submission['family_id']] = submission['insertion_date']
            else:
                most_recent_submission[submission['project_id']][submission['family_id']] = submission['insertion_date']
            
        else:
            most_recent_submission[submission['project_id']]= {submission['family_id'] : submission['insertion_date']}
    #make date serializable
    serializable_most_recent_submission={}
    for proj,families in most_recent_submission.iteritems():
        serializable_most_recent_submission[proj]=[]
        for f,v in families.iteritems():
            serializable_most_recent_submission[proj].append({"family_id":f, "insertion_date":str(v)})
    return serializable_most_recent_submission




def find_families_of_this_project_in_matchbox(project_id):
    """
    Find all families of this project with submissions in matchbox
    Returns:
        A dictionary with the key being a family name and the value being a dictionary with the
        keys being phenotype and genotype counts
        { 
            family_id:  {"phenotype_count": n, "genotype_count": n,"insertion_date:date"},
        }
    """
    all_submissions = settings.SEQR_ID_TO_MME_ID_MAP.find({'project_id':project_id})
    #the mongo query needs to be updated to do all this..
    most_recent_submission={}
    for submission in all_submissions:
        if most_recent_submission.has_key(submission['family_id']):
            if submission['insertion_date'] > most_recent_submission[submission['family_id']]["insertion_date"]:
                counts=count_genotypes_and_phenotypes(submission)
                most_recent_submission[submission['family_id']]= {"phenotype_count": counts["phenotype_count"], 
                                                                  "genotype_count": counts["genotype_count"],
                                                                  "insertion_date":submission['insertion_date'],
                                                                  "submitted_data":submission['submitted_data']}
        else:
            counts=count_genotypes_and_phenotypes(submission)
            most_recent_submission[submission['family_id']]= {"phenotype_count": counts["phenotype_count"], 
                                                            "genotype_count": counts["genotype_count"],
                                                            "insertion_date":submission['insertion_date'],
                                                            "submitted_data":submission['submitted_data']}
    #make date serializable
    serializable_most_recent_submission={}
    for family_id,counts in most_recent_submission.iteritems():
        serializable_most_recent_submission[family_id]={"phenotype_count": most_recent_submission[family_id]["phenotype_count"], 
                                                        "genotype_count":  most_recent_submission[family_id]["genotype_count"],
                                                        "insertion_date": str(most_recent_submission[family_id]['insertion_date']),
                                                        "submitted_data":submission['submitted_data']}
    return serializable_most_recent_submission


def count_genotypes_and_phenotypes(submission):
    """
    Given a submission record counts genotypes and phenotypes
    Args:
        A submission record from Mongo
    Returns:
        A dictionary that looks like  {"phenotype_count": n, "genotype_count": n}
        
    """
    try:
        return {"phenotype_count":len(submission['submitted_data']['patient']['features']), 
            "genotype_count": len(submission['submitted_data']['patient']['genomicFeatures'])}
    except:
        raise
    
    
def extract_hpo_id_list_from_mme_patient_struct(mme_patient_struct, hpo_details={}):
    """
    Given a MME patient structure, extracts HPO IDs and finds details on it
    Args:
        mme patient structure
    Returns:
        A map of HPO ID to its details such as name, description etc
    """
    if not mme_patient_struct['patient'].has_key('features'):
        return {}

    for feature in mme_patient_struct['patient']['features']:
        hpo_term = feature.get("id","")
        try:
            hpoDetails = HumanPhenotypeOntology.objects.get(hpo_id=hpo_term)
            hpo_details[hpo_term] = {
                "name": hpoDetails.name,
                "definition": hpoDetails.definition,
            }
        except ObjectDoesNotExist as e:
            logger.warning("HPO term '%s' cannot be found in local HPO map: %s" % (hpo_term, e))
            hpo_details[hpo_term] = {
                "name": hpo_term,
                "definition": "",
            }

    return hpo_details
        
        
