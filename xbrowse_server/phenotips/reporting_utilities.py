from xbrowse_server.base.models import Project
from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
import os
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth


def get_phenotype_entry_metrics_for_project(project_id):
    """
    Processes the given project

    Inputs:
        project_id: a project ID
    """
    try:
        project = Project.objects.get(project_id=project_id)
        external_ids = []
        for individual in project.get_individuals():
            external_ids.append(individual.phenotips_id)
        return get_phenotype_entry_details_for_individuals(project_id, external_ids)
    except Exception as e:
        print '\nsorry, we encountered an error finding project:', e, '\n'
        raise


"""-------DEPRACATED  --------------
def aggregate_phenotype_counts_into_bins(phenotype_counts):
   # Given a list of individual phenotype counts, aggregates these into
   # bins of counts
   # Input:
   # A list of dicts that have indiv ID and how many phenotypes entered
   # [{}, ....]
   # Ex:
   # [{'eid': u'NA19675', 'num_phenotypes_entered': 1},....]
    
   # Output:
   # A dict that resembles (the "count" here is derived from "num_phenotypes_entered":
  #  {count: [indiv1, indiv2, indiv3 ..indivs with this many phenotypes entered],
  #  count2: [indivX,...]}
  
  aggregated={}
  for count in phenotype_counts:
    if aggregated.has_key(count['num_phenotypes_entered']):
      aggregated[count['num_phenotypes_entered']].append(count['eid'])
    else:
      aggregated[count['num_phenotypes_entered']] = [count['eid']]
  return aggregated
"""


def get_phenotype_entry_details_for_individuals(project_id, external_ids):
    """
      Process this list of individuals
      
      Inputs:
        individuals: a list of individuals
    """
    all_patients = []

    for external_id in external_ids:
        phenotype_metrics_for_indiv = phenotype_entry_metric_for_individual(project_id, external_id)
        all_patients.append({'eid': external_id,
                             'num_phenotypes_entered': phenotype_metrics_for_indiv['count'],
                             'clinicalStatus': phenotype_metrics_for_indiv['clinicalStatus']
                             })
    return all_patients


"""DEPRACATED--------
def print_details_to_stdout(proj_dets,summarize):

    #Print details to STDOUT
   # 
   ## Inputs:
    #proj_dets: a project details structure
    #summarize: True/False whether to summarize view
  
  category_names=self.get_phenotype_count_categorie_names()
  if summarize:
      print '{:20s} {:20s} {:20s} {:20s} {:20s} {:20s}'.format('Project',*category_names)
  try:
    for proj_id,dets in proj_dets.iteritems():
      phenotype_counts={}
      for patient_det in dets:
        if not summarize:
          print patient_det['eid'],patient_det['num_phenotypes_entered']
        if summarize:
          if phenotype_counts.has_key(patient_det['num_phenotypes_entered']):
            phenotype_counts[patient_det['num_phenotypes_entered']].append(patient_det['eid'])
          else:
            phenotype_counts[patient_det['num_phenotypes_entered']]=[patient_det['eid']]
      if summarize:
        data=categorize_phenotype_counts(phenotype_counts)
        print '{:20s}'.format(proj_id),
        for category_name in category_names:
          print '{:20s}'.format(str(len(data[category_name]))),
        print
  except Exception as e:
    raise
"""

"""DEPRACTED ----
def categorize_phenotype_counts(phenotype_counts):
  
  ##  Bin counts in categories for easy reporting in columns
   # 
   # Categories are:
   # 0
   # 0-10
   # 10-20
   # >30
    
    Notes:
    If you add any new categories, remember to update method
    get_phenotype_count_categorie_names.
    
    Inputs:
    A dict of number of patients to number of phenotypes 
    entered for each patient 
    
    Outputs:
    -A dict with keys of above categories and values being count
    of each.
    -A tuple with category names
  
  category_names=get_phenotype_count_categorie_names()
  data={}
  for c in category_names:
    data[c]=[]
  for phenotype_count,patients in phenotype_counts.iteritems():
    if phenotype_count ==0:
      data['0'].extend(patients)
    if phenotype_count>0 and phenotype_count<11:
      data['1to10'].extend(patients) 
    if phenotype_count>=11 and phenotype_count<=20:
      data['11to20'].extend(patients)
    if phenotype_count>=21 and phenotype_count<=30:
      data['21to30'].extend(patients)
    if phenotype_count>=31:
      data['larger_than_31'].extend(patients)
  return data
"""

"""
DEPRACATED----
def get_phenotype_count_categorie_names():

    Return a tuple of category names used
    categorize_phenotype_counts.
    Notes:
    Any updates to this function must coincide with method
    
 
  return ('0','1to10','11to20','21to30','larger_than_31')
"""


def get_phenotypes_entered_for_individual(project_id, external_id):
    """
      Get phenotype data enterred for this individual.
      
      Inputs:
        external_id: an individual ID (ex: PIE-OGI855-001726)
    """
    try:
        uname, pwd = get_uname_pwd_for_project(project_id, read_only=True)
        url = os.path.join(settings.PHENOPTIPS_HOST_NAME, 'rest/patients/eid/' + external_id)
        response = requests.get(url, auth=HTTPBasicAuth(uname, pwd))
        return response.json()
    except Exception as e:
        print 'patient phenotype export error:', e
        raise


def phenotype_entry_metric_for_individual(project_id, external_id):
    """
      Determine a metric that describes the level of phenotype entry for this
      individual.
      
      Notes:
        1. Phenotype terms appear in both features (where HPO terms exist)
           and in nonstandard_features where phenotypes were defined in 
           regular text where HPO might not have existed.
      
      Inputs:
        1. external_id: an individual ID (ex: PIE-OGI855-001726)
      Returns:
        An object with the keys,
          i. 'clinicalStatus' : affected/unaffected
          ii.'count': number of phenotypes entered
      
    """
    entered_phenotypes = get_phenotypes_entered_for_individual(project_id, external_id)
    count = 0
    result = {}
    for k, v in entered_phenotypes.iteritems():
        if k == "clinicalStatus":
            result['clinicalStatus'] = v['clinicalStatus']
        if k == 'features' or k == 'nonstandard_features':
            count = count + len(v)
    result['phenotype_count'] = count
    return result
