import os
import logging
from django.conf import settings
import json
import urllib2
import base64
import requests
logger = logging.getLogger(__name__)
import sys
from xbrowse_server.base.models import Project
from django.shortcuts import get_object_or_404

def create_patient_record(individual_id,project_id,patient_details=None):
  '''
    Make a patient record:
  
    Create a patient record in phenotips.
    By convention username and password are project_id,project_idproject_id
    Authentication is protected by access to machine/localhost  
  
  '''
  uri = settings.PHENOPTIPS_HOST_NAME + '/bin/PhenoTips/OpenPatientRecord?create=true&eid=' + individual_id
  if patient_details is not None:
    uri += '&gender='+patient_details['gender']
  uname,pwd = get_uname_pwd_for_project(project_id)
  result,curr_session=do_authenticated_call_to_phenotips(uri,uname,pwd)
  if result is not None and result.status_code==200:
      print 'successfully created or updated patient',individual_id
      patient_eid = convert_internal_id_to_external_id(individual_id,uname,pwd)
      collaborator_username,collab_pwd=get_uname_pwd_for_project(project_id,read_only=True)
      add_read_only_user_to_phenotips_patient(collaborator_username,patient_eid)
  else:
      print 'error creating patient',individual_id,':',result
  
      

def do_authenticated_call_to_phenotips(url,uname,pwd,curr_session=None):
  '''
    Authenticates to phenotips, fetches (GET) given results and returns that
  '''
  try:
    if curr_session is None:
      s= requests.Session()
    else:
      s=curr_session
    result=s.get(url,auth=(uname,pwd))
    return result,s
  except Exception as e:
    raise


def convert_internal_id_to_external_id(int_id,project_phenotips_uname,project_phenotips_pwd):
  '''
    To help process a translation of internal id to external id 
  '''
  try:
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'rest/patients/eid/'+str(int_id))   
    result,curr_session = do_authenticated_call_to_phenotips(url,project_phenotips_uname,project_phenotips_pwd)
    if result.status_code != 200:
      raise Exception(("Failed to convert %s to internal id. Phenotips responded with HTTP status code: %s.  "
                      "Please check that the project and individual were previously created in Phenotips.") % (int_id, result.status_code))

    as_json = result.json()
    return as_json['id']
  except Exception as e:
    print 'convert internal id error:',e
    logger.error('phenotips.views.convert_internal_id_to_external_id:'+str(e))
    raise
  

def get_uname_pwd_for_project(project_name,read_only=False):
  '''
    Return the username and password for this project. 
    If read_only flag is true, only a read-only username will be returned
  '''
  pwd=project_name+project_name
  if not read_only:
    uname=project_name
    return uname,pwd
  uname=project_name+ '_view'
  return uname,pwd



def get_names_for_user(project_name,read_only=False):
  '''
    Returns the first and last name and password to be allocated for this project. 
    If read_only flag is true, the read-only equivalent is returned
  
    Returns a tuple: (first_name,last_name)
  '''
  #keeping last name empty for now, variable is mainly a place holder for the future
  last_name=''
  if not read_only:
    first_name=project_name
    return (first_name,last_name)
  first_name=project_name+ ' (view only)'
  return (first_name,last_name)

  '''
    TBD: we need to put this password in a non-checkin file:
    Generates a new user in phenotips
  '''
  admin_uname=settings.PHENOTIPS_ADMIN_UNAME
  admin_pwd=settings.PHENOTIPS_ADMIN_PWD
  headers={"Content-Type": "application/x-www-form-urlencoded"}
  data={'parent':'XWiki.XWikiUsers'}
  url = settings.PHENOPTIPS_HOST_NAME + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name
  do_authenticated_PUT(admin_uname,admin_pwd,url,data,headers) 
  data={'className':'XWiki.XWikiUsers',
        'property#first_name':new_user_first_name,
        'property#last_name':new_user_last_name,
        'property#email':email_address,
        'property#password':new_user_pwd
        }
  url=settings.PHENOPTIPS_HOST_NAME + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name + '/objects'
  do_authenticated_POST(admin_uname,admin_pwd,url,data,headers)
  
  

def add_read_only_user_to_phenotips_patient(username,patient_eid):
  '''
    Adds a non-owner phenotips-user to an existing patient. Requires an existing phenotips-user username, patient_eid (PXXXX..).
    Please note: User creation happens ONLY in method "add_new_user_to_phenotips". While this method 
    Is ONLY for associating an existing phenotips-username to a patient and with ONLY read-only capabilities. 
    It DOES NOT create the user account..
  '''
  admin_uname=settings.PHENOTIPS_ADMIN_UNAME
  admin_pwd=settings.PHENOTIPS_ADMIN_PWD
  headers={"Content-Type": "application/x-www-form-urlencoded"}
  data={'collaborator':'XWiki.' + username,
        'patient':patient_eid,
        'accessLevel':'view',
        'xaction':'update',
        'submit':'Update'}
  url = settings.PHENOPTIPS_HOST_NAME + '/bin/get/PhenoTips/PatientAccessRightsManagement?outputSyntax=plain'
  do_authenticated_POST(admin_uname,admin_pwd,url,data,headers)


def add_new_user_to_phenotips(new_user_first_name, new_user_last_name,new_user_name,email_address,new_user_pwd):
  '''
    TBD: we need to put this password in a non-checkin file:
    Generates a new user in phenotips
  '''
  admin_uname=settings.PHENOTIPS_ADMIN_UNAME
  admin_pwd=settings.PHENOTIPS_ADMIN_PWD
  headers={"Content-Type": "application/x-www-form-urlencoded"}
  data={'parent':'XWiki.XWikiUsers'}
  url = settings.PHENOPTIPS_HOST_NAME + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name
  do_authenticated_PUT(admin_uname,admin_pwd,url,data,headers) 
  data={'className':'XWiki.XWikiUsers',
        'property#first_name':new_user_first_name,
        'property#last_name':new_user_last_name,
        'property#email':email_address,
        'property#password':new_user_pwd
        }
  url=settings.PHENOPTIPS_HOST_NAME + '/rest/wikis/xwiki/spaces/XWiki/pages/' + new_user_name + '/objects'
  do_authenticated_POST(admin_uname,admin_pwd,url,data,headers)
  
  

def do_authenticated_PUT(uname,pwd,url,data,headers):
  '''
    Do a PUT call to phenotips
  '''
  try:
    request=requests.put(url,data=data,auth=(uname,pwd),headers=headers)
    return request
  except Exception as e:
    print 'error in do_authenticated_PUT:',e,
    raise
  

def do_authenticated_POST(uname,pwd,url,data,headers):
  '''
    Do a POST call to phenotips
  '''
  try:
    request=requests.post(url,data=data,auth=(uname,pwd),headers=headers)
  except Exception as e:
    print 'error in do_authenticated_POST:',e,
    raise
  
  
def get_auth_level(project_id,username):
  '''
    Determine the authentication level of this user based on xBrowse permissions.
    Returns a string that represents the auth level.
    
    -Auth levels (returned as strings):
     admin
     editor
     public
     viewer
    
    -Returns "unauthorized" if unauthorized.
    
  '''
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
  
  
def create_user_in_phenotips(project_id,project_name):
  '''
    Create usernames (a manager and read-only) that represents this project in phenotips  
  '''
  uname,pwd=get_uname_pwd_for_project(project_id)
  #first create a user with full write privileges
  first_name,last_name = get_names_for_user(project_name,read_only=False)
  add_new_user_to_phenotips(first_name,
                            last_name, 
                            uname,
                            settings.PHENOPTIPS_ALERT_CONTACT ,
                            pwd)
  print 'created a manager role in Phenotips ....'
  #Next create a user with ONLY VIEW privileges (the rights are determined when patients are added in)
  #Note: this step merely creates the user
  first_name,last_name = get_names_for_user(project_name,read_only=True)
  uname,pwd = get_uname_pwd_for_project(project_id,read_only=True)
  add_new_user_to_phenotips(first_name,
                            last_name, 
                            uname,
                            settings.PHENOPTIPS_ALERT_CONTACT ,
                            pwd)
  print 'created a read-only role in Phenotips ....'




def add_individuals_to_phenotips_from_vcf(individuals,project_id):
  '''
    Given a list of individuals using a VCF file add them to phenotips
  '''
  for individual in  individuals:        
    create_patient_record(individual,project_id)
    

def add_individuals_to_phenotips_from_ped(individual_details,project_id,):
  '''
    Given a list of individuals via a PED file, add them to phenotips 
    Note: using ONLY gender information from the PED file as of Jan 2016
  '''
  for individual in individual_details:
    id=individual['indiv_id']
    if individual['gender'] == 'female':
      extra_details={'gender': 'F'}
    elif individual['gender'] == 'male':
      extra_details={'gender': 'M'}
    elif individual['gender'] == 'unknown':
      extra_details=None
    else:
      raise ValueError("Unpexpected 'gender' value in individual %s" % str(individual))

    create_patient_record(id,project_id,extra_details)

  
