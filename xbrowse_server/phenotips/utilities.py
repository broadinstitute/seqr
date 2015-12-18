import os
import logging
from django.conf import settings
import json
import urllib2
import base64
import requests
logger = logging.getLogger(__name__)
import sys


def create_patient_record(individual_id,project_id,patient_details=None):
  '''
  make a patient record:
  
  create a patient record in phenotips
  by convention username and password are project_id,project_idproject_id
  authentication is protected by access to machine/localhost  
  
  '''
  uri = settings.PHENOPTIPS_HOST_NAME + '/bin/PhenoTips/OpenPatientRecord?create=true&eid=' + individual_id
  if patient_details is not None:
    uri += '&gender='+patient_details['gender']
  uname=project_id
  pwd=project_id+project_id
  result=do_authenticated_call_to_phenotips(uri,uname,pwd)
  if result is not None and result.getcode()==200:
      print 'successfully created or updated patient',individual_id
      patient_eid = convert_internal_id_to_external_id(individual_id,uname,pwd)
      collaborator_username,collab_pwd=get_generic_collaborator_uname_pwd_for_project(project_id)
      add_read_only_collaborator_phenotips_patient(collaborator_username,patient_eid)
  else:
      print 'error creating patient',individual_id,':',result
  
      

def do_authenticated_call_to_phenotips(url,uname,pwd):
  '''
  authenticates to phenotips, fetches (GET) given results and returns that
  '''

  try:
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    request = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (uname, pwd)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    result = urllib2.urlopen(request)   
    return result
  except Exception as e:
    return e
    


def convert_internal_id_to_external_id(int_id,project_phenotips_uname,project_phenotips_pwd):
  '''to help process a translation of internal id to external id '''
  try:
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'rest/patients/eid/'+str(int_id))   
    result = do_authenticated_call_to_phenotips(url,project_phenotips_uname,project_phenotips_pwd)
    as_json = json.loads(result.read())
    return as_json['id']
  except Exception as e:
    print 'convert internal id error:',e,result
    logger.error('phenotips.views:'+str(e) + ' : ' + str(result))
    return {'mapping':None,'error':str(e)}
  

def get_uname_pwd_for_project(project_name):
  '''
  return the username and password for this project
  '''
  uname=project_name
  pwd=project_name+project_name
  return uname,pwd



def get_generic_collaborator_uname_pwd_for_project(project_name):
  '''
  return the generic collaborator username and password for this project
  '''
  uname=project_name+ '_view'
  pwd=project_name+project_name
  return uname,pwd




def add_new_user_to_phenotips(new_user_first_name, new_user_last_name,new_user_name,email_address,new_user_pwd):
  '''
  TBD: we need to put this password in a non-checkin file:
  generates a new user in phenotips
  '''
  admin_uname='Admin'
  admin_pwd='admin'
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
  
  

def add_read_only_collaborator_phenotips_patient(collaborator_username,patient_eid):
  '''
  we need to put this password in a non-checkin file:
  adds a collaborator to an existing patient. Requires an existing collaborator username, patient_eid (PXXXX..)
  '''
  admin_uname='Admin'
  admin_pwd='admin'
  headers={"Content-Type": "application/x-www-form-urlencoded"}
  data={'collaborator':'XWiki.' + collaborator_username,
        'patient':patient_eid,
        'accessLevel':'view',
        'xaction':'update',
        'submit':'Update'}
  url = settings.PHENOPTIPS_HOST_NAME + '/bin/get/PhenoTips/PatientAccessRightsManagement?outputSyntax=plain'
  do_authenticated_POST(admin_uname,admin_pwd,url,data,headers)
  
  

def do_authenticated_PUT(uname,pwd,url,data,headers):
  '''
  do a PUT call to phenotips
  '''
  try:
    request=requests.put(url,data=data,auth=(uname,pwd),headers=headers)
  except Exception as e:
    print 'error in do_authenticated_PUT:',e,
    return e
  

def do_authenticated_POST(uname,pwd,url,data,headers):
  '''
  do a POST call to phenotips
  '''
  try:
    request=requests.post(url,data=data,auth=(uname,pwd),headers=headers)
  except Exception as e:
    print 'error in do_authenticated_POST:',e,
    return e