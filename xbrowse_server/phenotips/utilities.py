import os
import logging
from django.conf import settings
import json
import urllib2
import base64

logger = logging.getLogger(__name__)


#create a patient record in phenotips
def create_patient_record(individual_id):
  '''make a patient record'''
  uri = settings.PHENOPTIPS_HOST_NAME + '/bin/PhenoTips/OpenPatientRecord?create=true&eid=' + individual_id
  do_authenticated_call_to_phenotips(uri)
  
      
#authenticates to phenotips, fetches (GET) given results and returns that
def do_authenticated_call_to_phenotips(url):
  '''authenticates to phenotips, fetches (GET) given results and returns that'''
  try:
    uname=settings.PHENOTIPS_MASTER_USERNAME
    pwd=settings.PHENOTIPS_MASTER_PASSWORD 
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    request = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (uname, pwd)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    result = urllib2.urlopen(request)   
    return result
  except Exception as e:
    print 'error:',e
    
    

#to help process a translation of internal id to external id
def convert_internal_id_to_external_id(int_id):
  '''to help process a translation of internal id to external id '''
  try:
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'rest/patients/eid/'+int_id)    
    result = do_authenticated_call_to_phenotips(url)
    as_json = json.loads(result.read())
    return as_json['id']
  except Exception as e:
    print 'error:',e
    logger.error('phenotips.views:'+str(e))
    return {'mapping':None,'error':str(e)}