import fnmatch
import logging
import os
import requests
import json

from django.conf import settings
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Individual

from xbrowse_server.base.models import Project
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def create_patient_record(external_id, project_id, patient_details=None):
    """
    Make a patient record:
    
      Create a patient record in phenotips.
      By convention username and password are project_id,project_idproject_id
      Authentication is protected by access to machine/localhost
    """
    try:
        _create_patient_record_handler(external_id, project_id, patient_details=patient_details)
        print 'successfully created or updated patient', external_id
    except Exception as e:
        print e


def _create_patient_record_handler(external_id, project_id, patient_details=None):
    """
    Make a patient record:

      Create a patient record in phenotips.
      By convention username and password are project_id,project_idproject_id
      Authentication is protected by access to machine/localhost
    """
    uname, pwd = get_uname_pwd_for_project(project_id)
    url = settings.PHENOPTIPS_BASE_URL + '/rest/patients'
    headers = {"Content-Type": "application/json"}
    data = {'external_id': external_id}
    if patient_details:
        data.update(patient_details)
    result = do_authenticated_POST(uname, pwd, url, json.dumps(data), headers)
    if result is not None and result.status_code == 201:
        patient_id = result.headers['Location'].split('/')[-1]
        collaborator_username, collab_pwd = get_uname_pwd_for_project(project_id, read_only=True)
        add_read_only_user_to_phenotips_patient(collaborator_username, patient_id)
        return patient_id
    else:
        raise Exception('error creating patient {}: {}'.format(external_id, result))


def do_authenticated_call_to_phenotips(url, uname, pwd, curr_session=None):
    """
    Authenticates to phenotips, fetches (GET) given results and returns that
    """

    if curr_session is None:
        s = requests.Session()
    else:
        s = curr_session
    result = s.get(url, auth=(uname, pwd))
    return result, s


class PatientNotFoundError(StandardError):
    pass


def get_phenotips_internal_id(external_id, project_id, patient_details=None):
    """
    To help process a translation of external id (eg. seqr ID) to internal id (eg. the PhenoTips P00123 id)
    """

    url = os.path.join(settings.PHENOPTIPS_BASE_URL, 'rest/patients/eid/' + str(external_id))
    uname, pwd = get_uname_pwd_for_project(project_id)
    result, curr_session = do_authenticated_call_to_phenotips(url, uname, pwd)
    if result.status_code == 404:
        return _create_patient_record_handler(external_id, project_id, patient_details=patient_details)
    elif result.status_code != 200:
        raise Exception(("Failed to convert %s to internal id for unknown reasons (HTTP response code: %s, %s)") % (
                external_id, result.status_code, result.reason))

    as_json = result.json()
    return as_json['id']


def get_uname_pwd_for_project(project_id, read_only=False):
    """
    Return the username and password for this project.
    If read_only flag is true, only a read-only username will be returned
      
      WARNING: we relying on this simply method of authentication due to the protection awarded by
               the Broad firewall and closed ports and limited access to host machine. For those 
               using this system elsewhere we would suggest storing a unique hashed password
               in the database and this function could retrieve it from there and server, or atleast
               have a better password generation mechanism. Our current implementation was a first attempt
               and we plan to strengthen this further soon.
    """
    pwd = project_id + project_id
    if not read_only:
        uname = project_id
        return uname, pwd
    uname = project_id + '_view'
    return uname, pwd


def get_names_for_user(project_name, read_only=False):
    """
    Returns the first and last name and password to be allocated for this project.
    If read_only flag is true, the read-only equivalent is returned
    
    Returns a tuple: (first_name,last_name)
    """
    # keeping last name empty for now, variable is mainly a place holder for the future
    last_name = ''
    if not read_only:
        first_name = project_name
        return (first_name, last_name)
    first_name = project_name + ' (view only)'
    return (first_name, last_name)

    """
      TBD: we need to put this password in a non-checkin file:
      Generates a new user in phenotips
    """
    admin_uname = settings.PHENOTIPS_ADMIN_UNAME
    admin_pwd = settings.PHENOTIPS_ADMIN_PWD
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {'parent': 'XWiki.XWikiUsers'}
    url = settings.PHENOPTIPS_BASE_URL + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name
    do_authenticated_PUT(admin_uname, admin_pwd, url, data, headers)
    data = {'className': 'XWiki.XWikiUsers',
            'property#first_name': new_user_first_name,
            'property#last_name': new_user_last_name,
            'property#email': email_address,
            'property#password': new_user_pwd
            }
    url = settings.PHENOPTIPS_BASE_URL + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name + '/objects'
    do_authenticated_POST(admin_uname, admin_pwd, url, data, headers)


def add_read_only_user_to_phenotips_patient(username, patient_id):
    """
    Adds a non-owner phenotips-user to an existing patient. Requires an existing phenotips-user username, patient_eid (PXXXX..).
    Please note: User creation happens ONLY in method "add_new_user_to_phenotips". While this method
    Is ONLY for associating an existing phenotips-username to a patient and with ONLY read-only capabilities.
    It DOES NOT create the user account..
    """
    admin_uname = settings.PHENOTIPS_ADMIN_UNAME
    admin_pwd = settings.PHENOTIPS_ADMIN_PWD
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {'collaborator': 'XWiki.' + username,
            'patient': patient_id,
            'accessLevel': 'view',
            'xaction': 'update',
            'submit': 'Update'}
    url = settings.PHENOPTIPS_BASE_URL + '/bin/get/PhenoTips/PatientAccessRightsManagement?outputSyntax=plain'
    do_authenticated_POST(admin_uname, admin_pwd, url, data, headers)


def add_new_user_to_phenotips(new_user_first_name, new_user_last_name, new_user_name, email_address, new_user_pwd):
    """
    TBD: we need to put this password in a non-checkin file:
    Generates a new user in phenotips
    """
    admin_uname = settings.PHENOTIPS_ADMIN_UNAME
    admin_pwd = settings.PHENOTIPS_ADMIN_PWD
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {'parent': 'XWiki.XWikiUsers'}
    url = settings.PHENOPTIPS_BASE_URL + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name
    do_authenticated_PUT(admin_uname, admin_pwd, url, data, headers)
    data = {'className': 'XWiki.XWikiUsers',
            'property#first_name': new_user_first_name,
            'property#last_name': new_user_last_name,
            'property#email': email_address,
            'property#password': new_user_pwd
            }
    url = settings.PHENOPTIPS_BASE_URL + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name + '/objects'
    do_authenticated_POST(admin_uname, admin_pwd, url, data, headers)


def do_authenticated_PUT(uname, pwd, url, data, headers):
    """
      Do a PUT call to phenotips
    """
    try:
        request = requests.put(url, data=data, auth=(uname, pwd), headers=headers)
        return request
    except Exception as e:
        print 'error in do_authenticated_PUT:', e,
        raise

def do_authenticated_POST(uname, pwd, url, data, headers):
    """
      Do a POST call to phenotips
    """
    try:
        request = requests.post(url, data=data, auth=(uname, pwd), headers=headers)
        return request
    except Exception as e:
        print 'error in do_authenticated_POST:', e,
        raise


def get_auth_level(project_id, username):
    """
      Determine the authentication level of this user based on xBrowse permissions.
      Returns a string that represents the auth level.
      
      -Auth levels (returned as strings):
       admin
       editor
       public
       viewer
      
      -Returns "unauthorized" if unauthorized.
      
    """
    project = get_object_or_404(Project, project_id=project_id)
    if project.can_admin(username):
        return 'admin'
    elif project.can_edit(username):
        return 'editor'
    elif project.is_public:
        return 'public'
    elif project.can_view(username):
        return 'viewer'
    else:
        return "unauthorized"


def create_user_in_phenotips(project_id, project_name):
    """
    Create usernames (a manager and read-only) that represents this project in phenotips
    """
    uname, pwd = get_uname_pwd_for_project(project_id)
    # first create a user with full write privileges
    first_name, last_name = get_names_for_user(project_name, read_only=False)
    add_new_user_to_phenotips(first_name,
                              last_name,
                              uname,
                              settings.PHENOPTIPS_ALERT_CONTACT,
                              pwd)
    print 'created a manager role in Phenotips ....'
    # Next create a user with ONLY VIEW privileges (the rights are determined when patients are added in)
    # Note: this step merely creates the user
    first_name, last_name = get_names_for_user(project_name, read_only=True)
    uname, pwd = get_uname_pwd_for_project(project_id, read_only=True)
    add_new_user_to_phenotips(first_name,
                              last_name,
                              uname,
                              settings.PHENOPTIPS_ALERT_CONTACT,
                              pwd)
    print 'created a read-only role in Phenotips ....'


def add_individuals_to_phenotips(project_id, individual_ids=None):
    """
    Given a list of individual ids, create new patient records for them in PhenoTips.

    Args:
        project_id: seqr project id
        individual_ids: (optional) Individual ids from seqr. These individuals must already exist in this project in seqr.
            If set to None, all individuals in the given project will be added to PhenoTips.

    """
    if individual_ids is None:
        individual_ids = [i.indiv_id for i in Individual.objects.filter(project__project_id=project_id)]

    for individual_id in individual_ids:
        try:
            indiv = Individual.objects.get(project__project_id=project_id, indiv_id=individual_id)
        except Exception as e:
            print("Error: %s on %s" % (e, individual_id))
            continue

        assert indiv.gender in ['M', 'F', 'U'], "Unexpected value for gender in %s : %s " % (indiv, indiv.gender)

        # check whether the patient already exists and create them if not
        get_phenotips_internal_id(indiv.phenotips_id, project_id, patient_details={'gender': indiv.gender})


def add_individuals_with_details_to_phenotips(individual_details, project_id):
    """
    DEPRECATED: Use add_individuals_to_phenotips instead

      Given a list of individuals via a PED file, add them to phenotips
      Note: using ONLY gender information from the PED file as of Jan 2016
    """
    for individual in individual_details:
        indiv_id = individual['indiv_id']
        if individual['gender'] == 'female':
            extra_details = {'gender': 'F'}
        elif individual['gender'] == 'male':
            extra_details = {'gender': 'M'}
        elif individual['gender'] == 'unknown':
            extra_details = None
        else:
            raise ValueError("Unpexpected 'gender' value in individual %s" % str(individual))

        create_patient_record(indiv_id, project_id, extra_details)


def find_db_files(install_dir):
    """
      Look and return a list of files with full path with extension '*.xed' 
    """
    target_extension = '*.xed'
    targets = []
    for root, dirs, files in os.walk(install_dir):
        for name in files:
            if fnmatch.fnmatch(name, target_extension):
                targets.append(os.path.join(root, name))
    return targets


def find_references(file_names, temp_dir):
    """
      find DB references
    """
    look_for = '<installed.installed type="boolean">true</installed.installed>'
    tmp_file = os.path.join(temp_dir, 'tmp.txt')
    replace_count = 0
    for file_name in file_names:
        with open(tmp_file, 'w')as tmp_out:
            with open(file_name.rstrip(), 'r') as file_in:
                for line in file_in:
                    if look_for in line:
                        replace_count += 1
                        adjusted = line.replace('true', 'false')
                        line = adjusted
                    tmp_out.write(line)
        tmp_out.close()
        # now replace with updated version
        cp_cmd = ['cp', tmp_file, file_name]
        os.system(' '.join(cp_cmd))
    print('adjusted line count:', replace_count)


def get_phenotypes_entered_for_individual(project_id, external_id):
    """
    Get phenotype data entered for this individual.
      
    Args:
        project_id (string): project ID for this ID
        external_id (string): an individual ID (ex: PIE-OGI855-001726)
        
    Returns:
        JSONresponse: phenotypes 
    """
    try:
        uname, pwd = get_uname_pwd_for_project(project_id, read_only=False)
        url = os.path.join(settings.PHENOPTIPS_BASE_URL, 'rest/patients/eid/' + external_id)
        response = requests.get(url, auth=HTTPBasicAuth(uname, pwd))
        logger.info(response.text)
        return response.json()
    except Exception as e:
        logger.info('patient phenotype export error: %s', e)
        raise


def validate_phenotips_upload(uploaded, found_in_phenotips):
    """
    Compare these two JSON structures
    
    Args:
        uploaded (dict): are data that were intended to be inserted into local PhenoTips instance
        found_in_phenotips (dict): are data that is expected to have been uploaded
    
    Returns:
        dict: 'missing' key maps to keys found in data that was sent to phenoptypes but missing in local PhenoTips, 
              'found' is when key is found in both
    """
    status = {"found": [], "missing": []}
    for k, v in uploaded.iteritems():
        if found_in_phenotips.has_key(k):
            status['found'].append({k:v})
        else:            
            status['missing'].append({k:v})
    return status


def merge_phenotype_data(uploaded_phenotype_data,existing_phenotypes):
    """
    Given two JSON structures of phenotypes, return a superset of merged data
    
    Args:
        uploaded_phenotype_data (dict): 
        existing_phenotypes (dict):
        
    Returns:
        dict: merged set of data
        
    """
    if not existing_phenotypes.has_key('features'):
        existing_phenotypes['features']=[]
    for hpo_obj in uploaded_phenotype_data['features']:
        existing_phenotypes['features'].append(hpo_obj)
        logger.info(hpo_obj)
    return existing_phenotypes


