from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
import datetime
import time
import os
from xbrowse_server.decorators import log_request
import ast
import logging
from django.http.response import HttpResponse
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
import requests
from xbrowse_server.phenotips.utilities import do_authenticated_call_to_phenotips
from xbrowse_server.phenotips.utilities import convert_internal_id_to_external_id
    
logger = logging.getLogger(__name__)

  
@log_request('phenotips_proxy_edit_page')
@login_required
#test function to see if we can proxy phenotips
def fetch_phenotips_edit_page(request,eid):
  '''test function to see if we can proxy phenotips'''
  print request.user.username,'<<'
  url= settings.PHENOPTIPS_HOST_NAME+'/bin/edit/data/'+ convert_internal_id_to_external_id(eid)
  result = do_authenticated_call_to_phenotips(url)
  return __add_back_phenotips_headers_response(result)


def proxy_get(request):
  '''to act as a proxy for get requests '''
  try:
    result = do_authenticated_call_to_phenotips(__aggregate_url_parameters(request))
    return __add_back_phenotips_headers_response(result)
  except Exception as e:
    print e
    logger.error('phenotips.views:'+str(e))
    raise Http404
  

#given a request object,and base URL aggregates and returns a reconstructed URL
def __aggregate_url_parameters(request):
  '''given a request object, aggregates and returns parameters'''
  counter=0
  url=settings.PHENOPTIPS_HOST_NAME+request.path + '?'
  for param,val in request.GET.iteritems():
    url += param + '=' + val
    if counter < len(request.GET)-1:
      url += '&'
    counter+=1
  return url

#exempting csrf here since phenotips doesn't have this support
@csrf_exempt
def proxy_post(request):
  '''to act as a proxy  '''
  print request.path,'------<<'
  try:    
    if len(request.POST) != 0 and request.POST.has_key('PhenoTips.PatientClass_0_external_id'):
      print 'sync!'
      __process_sync_request_helper(request.POST['PhenoTips.PatientClass_0_external_id'])
    #re-construct proxy-ed URL again
    url=settings.PHENOPTIPS_HOST_NAME+request.path
    uname=settings.PHENOTIPS_MASTER_USERNAME
    pwd=settings.PHENOTIPS_MASTER_PASSWORD   
    resp = requests.post(url, data=request.POST, auth=(uname,pwd))
    response = HttpResponse(resp.text)
    for k,v in resp.headers.iteritems():
      response[k]=v
    return response
  except Exception as e:
    print 'error:',e
    logger.error('phenotips.views:'+str(e))
    raise Http404
  
  
#process a synchronization between xbrowse and phenotips
def __process_sync_request_helper(int_id):
  '''sync data of this user between xbrowse and phenotips'''  
  try:
    #first get the newest data via API call
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'bin/get/PhenoTips/ExportPatient?eid='+int_id)
    result = do_authenticated_call_to_phenotips(url)
    print result.read() #this should change into a xBrowse update
    return True
  except Exception as e:
    print 'error:',e
    logger.error('phenotips.views:'+str(e))
    return False
  
#add the headers generated from phenotips server back to response object
def __add_back_phenotips_headers_response(result):
  headers=result.info()
  response = HttpResponse(result.read())
  for k in headers.keys():
    if k != 'connection': #this hop-by-hop header is not allowed by Django
      response[k]=headers[k]
  return response

  

    
    
    