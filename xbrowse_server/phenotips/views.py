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
from xbrowse_server.phenotips.utilities import get_auth_level
import json

from xbrowse_server.base.models import Project
from django.shortcuts import render, redirect, get_object_or_404
from json.decoder import JSONDecoder
from StdSuites.AppleScript_Suite import result
  
logger = logging.getLogger(__name__)

  
  
@log_request('phenotips_proxy_edit_page')
@login_required
@csrf_exempt
def fetch_phenotips_edit_page(request,eid):
  '''
    A proxy for phenotips view and edit patient pages
    Note: exempting csrf here since phenotips doesn't have this support
  '''  
  try:
    current_user = request.user
    if request.GET.has_key('project'):
      project_id=request.GET['project']  
      #adding project id and ext_id to session for later use in proxying
      request.session['current_project_id']=project_id
      admin__uname,admin_pwd = get_uname_pwd_for_project(project_id)
      ext_id=convert_internal_id_to_external_id(eid,admin__uname,admin_pwd)
  
      request.session['current_ext_id']=ext_id
      auth_level=get_auth_level(project_id,request.user)
      if auth_level == 'unauthorized':
        return HttpResponse('unauthorized')
    else: 
      project_id = request.session['current_project_id']
      ext_id=request.session['current_ext_id']
      auth_level=get_auth_level(request.session['current_project_id'],request.user)
      if auth_level == 'unauthorized':
        return HttpResponse('unauthorized')
    if auth_level=='admin':
      phenotips_uname,phenotips_pwd = get_uname_pwd_for_project(project_id,read_only=False)
    else:
      phenotips_uname,phenotips_pwd  = get_uname_pwd_for_project(project_id,read_only=True)
    url= settings.PHENOPTIPS_HOST_NAME+'/bin/'+ ext_id
    if auth_level=='admin':
      url= settings.PHENOPTIPS_HOST_NAME+'/bin/edit/data/'+ ext_id
    if not request.GET.has_key('project'):
      url += '?'
      counter=0
      for param,val in request.GET.iteritems():
        url += param + '=' + val
        if counter < len(request.GET)-1:
          url += '&'
        counter+=1
    result = do_authenticated_call_to_phenotips(url,phenotips_uname,phenotips_pwd)
    response = __add_back_phenotips_headers_response(result)
    return response
  except:
    raise Http404 



@log_request('proxy_get')
@login_required
@csrf_exempt
def proxy_get(request):
  '''
      To act as a proxy for get requests for Phenotips
      Note: exempting csrf here since phenotips doesn't have this support
  '''
  project_name = request.session['current_project_id']
  project_phenotips_uname,project_phenotips_pwd = get_uname_pwd_for_project(project_name)
  try:
    result = do_authenticated_call_to_phenotips(__aggregate_url_parameters(request),project_phenotips_uname,project_phenotips_pwd)
    return __add_back_phenotips_headers_response(result)
  except Exception as e:
    print 'proxy get error:',e
    logger.error('phenotips.views:'+str(e))
    raise Http404



def __aggregate_url_parameters(request):
  '''
      Given a request object,and base URL aggregates and returns a reconstructed URL
  '''
  counter=0
  url=settings.PHENOPTIPS_HOST_NAME+request.path + '?'
  for param,val in request.GET.iteritems():
    url += param + '=' + val
    if counter < len(request.GET)-1:
      url += '&'
    counter+=1
  return url



@csrf_exempt
@log_request('proxy_post')
@login_required
def proxy_post(request):
  '''
      To act as a proxy for POST requests from Phenotips
      note: exempting csrf here since phenotips doesn't have this support
  '''
  try:    
    #re-construct proxy-ed URL again
    url=settings.PHENOPTIPS_HOST_NAME+request.get_full_path()
    project_name = request.session['current_project_id']
    uname,pwd = get_uname_pwd_for_project(project_name)
    resp = requests.post(url, data=request.POST, auth=(uname,pwd))
    response = HttpResponse(resp.text)
    for k,v in resp.headers.iteritems():
      response[k]=v
    #save the update in mongo 
    if len(request.POST) != 0:# and request.POST.has_key('PhenoTips.PatientClass_0_external_id'):
      project_name = request.session['current_project_id']
      uname,pwd = get_uname_pwd_for_project(project_name)
      #ext_id=request.POST['PhenoTips.PatientClass_0_external_id']
      ext_id=request.session['current_ext_id']
      __process_sync_request_helper(ext_id,
                                    uname,
                                    pwd,
                                    request.user.username,
                                    project_name)
    return response
  except Exception as e:
    print 'proxy post error:',e
    logger.error('phenotips.views:'+str(e))
    raise Http404
  
  

def __process_sync_request_helper(int_id,uname,pwd,xbrowse_username,project_name):
  '''
      Sync data of this user between xbrowse and phenotips. Persists the update in a 
      database for later searching and edit audits.
  '''  
  try:
    #first get the newest data via API call
    url= os.path.join(settings.PHENOPTIPS_HOST_NAME,'bin/get/PhenoTips/ExportPatient?eid='+int_id)
    result = do_authenticated_call_to_phenotips(url,uname,pwd)
    updated_patient_record=json.dumps(json.JSONDecoder().decode(result.read()))
    settings.PHENOTIPS_EDIT_AUDIT.insert({
                                          'xbrowse_username':xbrowse_username,
                                          'updated_patient_record':updated_patient_record,
                                          'project_name':project_name,
                                          'patient_id':int_id,
                                          'time':datetime.datetime.now()
                                          })
    return True
  except Exception as e:
    print 'sync request error:',e
    logger.error('phenotips.views:'+str(e))
    return False
  

def __add_back_phenotips_headers_response(result):
  '''
      Add the headers generated from phenotips server back to response object
  '''
  print '----'


  headers=result.info()
  response = HttpResponse(result.read())
  for k in headers.keys():
    print k,headers[k]
    if k != 'connection': #this hop-by-hop header is not allowed by Django
      response[k]=headers[k]
      
  print '----'
  return response

  

    
    
    