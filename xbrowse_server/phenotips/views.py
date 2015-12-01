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
from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
    
logger = logging.getLogger(__name__)

  
@log_request('phenotips_proxy_edit_page')
@login_required
#test function to see if we can proxy phenotips
def fetch_phenotips_edit_page(request,eid):
  '''test function to see if we can proxy phenotips'''
  project_name=request.GET['project']
  project_phenotips_uname,project_phenotips_pwd = get_uname_pwd_for_project(project_name)
  ext_id=convert_internal_id_to_external_id(eid,project_phenotips_uname,project_phenotips_pwd)
  if type(ext_id) != dict:
    url= settings.PHENOPTIPS_HOST_NAME+'/bin/edit/data/'+ ext_id
    #we are using the project name as the username and project name twice as the password
    #for example if project name was foo, the username would be foo, password would be foofoo
    result = do_authenticated_call_to_phenotips(url,project_phenotips_uname,project_phenotips_pwd)
    response = __add_back_phenotips_headers_response(result)
    #add project name as a header as well for use in proxying
    response.set_cookie('current_project_name',project_name)
    return response
  else:
    logger.error('phenotips.views:'+ext_id['error'])
    raise Http404    


#do a GET as a proxy for Phenotips
def proxy_get(request):
  '''to act as a proxy for get requests '''
  project_name = request.COOKIES['current_project_name' ]
  project_phenotips_uname,project_phenotips_pwd = get_uname_pwd_for_project(project_name)
  try:
    result = do_authenticated_call_to_phenotips(__aggregate_url_parameters(request),project_phenotips_uname,project_phenotips_pwd)
    return __add_back_phenotips_headers_response(result)
  except Exception as e:
    print 'proxy get error:',e
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

#do a POST as a proxy for Phenotips
#exempting csrf here since phenotips doesn't have this support
@csrf_exempt
def proxy_post(request):
  '''to act as a proxy  '''
  try:    
    if len(request.POST) != 0 and request.POST.has_key('PhenoTips.PatientClass_0_external_id'):
      print 'sync!'
      project_name = request.COOKIES['current_project_name' ]
      uname,pwd = get_uname_pwd_for_project(project_name)
      __process_sync_request_helper(request.POST['PhenoTips.PatientClass_0_external_id'],uname,pwd)
    #re-construct proxy-ed URL again
    url=settings.PHENOPTIPS_HOST_NAME+request.path
    project_name=request.COOKIES['current_project_name' ]
    uname,pwd = get_uname_pwd_for_project(project_name)
    resp = requests.post(url, data=request.POST, auth=(uname,pwd))
    response = HttpResponse(resp.text)
    for k,v in resp.headers.iteritems():
      response[k]=v
    return response
  except Exception as e:
    print 'proxy post error:',e
    logger.error('phenotips.views:'+str(e))
    raise Http404
  
  
#process a synchronization between xbrowse and phenotips
def __process_sync_request_helper(int_id,uname,pwd):
  '''sync data of this user between xbrowse and phenotips'''  
  try:
    #first get the newest data via API call
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'bin/get/PhenoTips/ExportPatient?eid='+int_id)
    result = do_authenticated_call_to_phenotips(url,uname,pwd)
    print result.read() #this should change into a xBrowse update
    return True
  except Exception as e:
    print 'sync request error:',e
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

  

    
    
    