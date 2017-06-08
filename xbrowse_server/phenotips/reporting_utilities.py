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
    result = {"raw":entered_phenotypes}
    for k, v in entered_phenotypes.iteritems():
        if k == "clinicalStatus":
            result['clinicalStatus'] = v['clinicalStatus']
        if k == 'features' or k == 'nonstandard_features':
            count = count + len(v)
    result['phenotype_count'] = count
    return result



def get_phenotypes_entered_for_individual(project_id, external_id):
    """
      Get phenotype data enterred for this individual.
      
      Inputs:
        external_id: an individual ID (ex: PIE-OGI855-001726)
    """
    try:
        uname, pwd = get_uname_pwd_for_project(project_id, read_only=True)
        url = os.path.join(settings.PHENOPTIPS_HOST_NAME, 'rest/patients/eid/' + external_id)
        #temp debug
        print ">>> phenotips API call:",url
        response = requests.get(url, auth=HTTPBasicAuth(uname, pwd))
        #temp error message to track tricky bug
        print ">>> phenotips API call response_state:",response.status_code,response.text
        if 404 != response.status_code:
            return response.json()
        return {}
    except Exception as e:
        print 'patient phenotype export error:', e
        raise
