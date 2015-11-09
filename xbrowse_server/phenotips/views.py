from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import urllib2
import base64
from django.conf import settings
import datetime
import time
import os
from xbrowse_server.decorators import log_request
import ast
import json
import logging
logger = logging.getLogger(__name__)

@log_request('sync_data_api')
@login_required
#handle a request to sync data between xbrowse and phenotips
def process_sync_request(request):
  '''handle a request to sync data'''
  message={'message':'meant for AJAX POST'}
  if request.method == 'POST':
      if request.is_ajax():
          uname = request.POST.get('uname')
          pwd = request.POST.get('pwd')
          individual_id=request.POST.get('id')
          if __process_sync_request_helper(uname,pwd,individual_id):
            message={'status':'success'}
          else:
            message={'status':'error'}
  return JsonResponse(message)


#process a synchronization between xbrowse and phenotips
def __process_sync_request_helper(uname,pwd,eid):
  '''sync data of this user between xbrowse and phenotips'''  
  print uname,pwd,eid,'<<'
  try:
    #first get the newest data via API call
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'bin/get/PhenoTips/ExportPatient?eid='+eid)
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    request = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (uname, pwd)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    result = urllib2.urlopen(request)   
    return True
  except Exception as e:
    logger.error('phenotips.views:'+str(e))
    return False
  
  
@log_request('internal_id_api')
@login_required
#handle a request to get phenotips data of a ilst of internal ids (NAxxxx or individual)
def process_internal_id(request):
  '''handle a request to get phenotips data of a list of internal ids (NAxxxx or individual)'''
  message={'message':'meant for AJAX POST'}
  if request.method == 'POST':
      if request.is_ajax():
          uname = request.POST.get('uname')
          pwd = request.POST.get('pwd')
          data = request.POST.get('data')
          details = __process_internal_id_helper(uname,pwd,data)
          if details['mapping'] is not None:
            message={'status':'success', 'mapping':details['mapping']}
          else:
            message={'status':'error','error':details['error']} 
  return JsonResponse(message)


#to help process a translation of internal id to external id
def __process_internal_id_helper(uname,pwd,data):
  '''to help process a translation of internal id to external id '''
  mapping=[]
  try:
    for i,v in enumerate(ast.literal_eval(data)):
      url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'rest/patients/eid/'+v)
      print url
      password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
      request = urllib2.Request(url)
      base64string = base64.encodestring('%s:%s' % (uname, pwd)).replace('\n', '')
      request.add_header("Authorization", "Basic %s" % base64string)   
      result = urllib2.urlopen(request)
      as_json = json.loads(result.read())
      mapping.append({'internal_id':v,'external_id':as_json['id']})
    return {'mapping':mapping,'error':''}
  except Exception as e:
    logger.error('phenotips.views:'+str(e))
    return {'mapping':None,'error':str(e)}
  
    