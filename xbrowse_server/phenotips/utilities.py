import os
import logging
from django.conf import settings
import json
import urllib2
import base64

logger = logging.getLogger(__name__)


#create a patient record in phenotips
#by convention username and password are project_id,project_idproject_id
#authentication is protected by access to machine/localhost
def create_patient_record(individual_id,project_id):
  '''make a patient record'''
  uri = settings.PHENOPTIPS_HOST_NAME + '/bin/PhenoTips/OpenPatientRecord?create=true&eid=' + individual_id
  uname=project_id
  pwd=project_id+project_id
  result=do_authenticated_call_to_phenotips(uri,uname,pwd)
  if result is not None and result.getcode()==200:
      print 'successfully created or updated patient',individual_id
  else:
      print 'error creating patient',individual_id,':',result
  
      
#authenticates to phenotips, fetches (GET) given results and returns that
def do_authenticated_call_to_phenotips(url,uname,pwd):
  '''authenticates to phenotips, fetches (GET) given results and returns that'''
  try:
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    request = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (uname, pwd)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    result = urllib2.urlopen(request)   
    return result
  except Exception as e:
    return e
    

#to help process a translation of internal id to external id
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
  
#return the username and password for this project
def get_uname_pwd_for_project(project_name):
  uname=project_name
  pwd=project_name+project_name
  return uname,pwd


#generates a new user in phenotips
def add_new_user_to_phenotips(project_name):
  pass
  