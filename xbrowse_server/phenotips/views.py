from django.contrib.auth.decorators import login_required
from django.conf import settings
import datetime

import json
import os
import sys
from xbrowse_server.decorators import log_request
import logging
from django.http.response import HttpResponse
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from xbrowse_server.phenotips.utilities import do_authenticated_call_to_phenotips
from xbrowse_server.phenotips.utilities import convert_external_id_to_internal_id
from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
from xbrowse_server.phenotips.utilities import get_auth_level
from xbrowse_server.base.models import Individual
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from django.shortcuts import render
from xbrowse_server.server_utils import JSONResponse

from django.core.exceptions import PermissionDenied
import pickle
from symbol import parameters

logger = logging.getLogger(__name__)


@log_request('phenotips_proxy_edit_page')
@login_required
@csrf_exempt
def fetch_phenotips_edit_page(request, eid):
    """
    A proxy for phenotips view and edit patient pages
    Note: exempting csrf here since phenotips doesn't have this support
    """
    try:
        current_user = request.user
        # if projectID key is found in in GET, it is the first connection call from browser
        if request.GET.has_key('project'):
            # adding project id and patient_id to session for later use in proxying
            project_id = request.GET['project']
            request.session['current_project_id'] = project_id
            admin_uname, admin_pwd = get_uname_pwd_for_project(project_id)
            patient_id = convert_external_id_to_internal_id(eid, admin_uname, admin_pwd)
            request.session['current_patient_id'] = patient_id
            auth_level = get_auth_level(project_id, request.user)
            if auth_level == 'unauthorized':
                raise PermissionDenied

            if auth_level == 'admin':
                phenotips_uname, phenotips_pwd = get_uname_pwd_for_project(project_id, read_only=False)
            else:
                phenotips_uname, phenotips_pwd = get_uname_pwd_for_project(project_id, read_only=True)
            url = settings.PHENOPTIPS_BASE_URL + '/bin/' + patient_id
            if auth_level == 'admin':
                url = settings.PHENOPTIPS_BASE_URL + '/bin/edit/data/' + patient_id
            response, curr_session = do_authenticated_call_to_phenotips(url, phenotips_uname, phenotips_pwd)
            # save this session with PhenoTips in current seqr session to be used within it to prevent
            # re-authenticating
            request.session['current_phenotips_session'] = pickle.dumps(curr_session)
            http_response = HttpResponse(response.content)
            for header in response.headers.keys():
                http_response[header] = response.headers[header]
            return http_response

        # this is a subsequent call made during the opening of the frame by phenotips
        # and will use session info for required variables
        else:
            project_id = request.session['current_project_id']
            patient_id = request.session['current_patient_id']
            auth_level = get_auth_level(request.session['current_project_id'], request.user)
            if auth_level == 'unauthorized':
                raise PermissionDenied

        if auth_level == 'admin':
            phenotips_uname, phenotips_pwd = get_uname_pwd_for_project(project_id, read_only=False)
        else:
            phenotips_uname, phenotips_pwd = get_uname_pwd_for_project(project_id, read_only=True)
        url = settings.PHENOPTIPS_BASE_URL + '/bin/' + patient_id
        if auth_level == 'admin':
            url = settings.PHENOPTIPS_BASE_URL + '/bin/edit/data/' + patient_id
        if not request.GET.has_key('project'):
            url += '?'
            counter = 0
            for param, val in request.GET.iteritems():
                url += param + '=' + val
                if counter < len(request.GET) - 1:
                    url += '&'
                counter += 1

        # pedigree editor is special
        if 'sheet' in request.GET.keys():
            url += '#'

        # get back a session and a result
        curr_session = pickle.loads(request.session['current_phenotips_session'])
        response, _ = do_authenticated_call_to_phenotips(url, phenotips_uname, phenotips_pwd, curr_session)
        http_response = HttpResponse(response.content)
        for header in response.headers.keys():
            http_response[header] = response.headers[header]
        return http_response
    except Exception as e:
        print e
        raise Http404


@log_request('phenotips_proxy_pdf_page')
@login_required
@csrf_exempt
def fetch_phenotips_pdf_page(request, eid):
    """
    A proxy for phenotips view and edit patient pages
    Notes:
        - Exempting csrf here since phenotips doesn't have this support
        - Each call to this endpoint is atomic, no session information is kept
          between calls. Each call to this is from within a new Frame, hence no
          notion of session is kept. Each is a new login into PhenoTips.
    """
    try:
        current_user = request.user
        project_id = request.GET['project']
        uname, pwd = get_uname_pwd_for_project(project_id, read_only=True)
        patient_id = convert_external_id_to_internal_id(eid, uname, pwd)
        auth_level = get_auth_level(project_id, request.user)
        if auth_level == 'unauthorized':
            raise PermissionDenied

        url = settings.PHENOPTIPS_BASE_URL + '/bin/export/data/' + patient_id + '?format=pdf&pdfcover=0&pdftoc=0&pdftemplate=PhenoTips.PatientSheetCode'
        response, curr_session = do_authenticated_call_to_phenotips(url, uname, pwd)
        http_response = HttpResponse(response.content)
        for header in response.headers.keys():
            if header != 'connection' and header != 'Transfer-Encoding':  # these hop-by-hop headers are not allowed by Django
                http_response[header] = response.headers[header]
        return http_response
    except Exception as e:
        print e
        raise Http404


@log_request('proxy_get')
@login_required
@csrf_exempt
def proxy_get(request):
    """
        To act as a proxy for get requests for Phenotips
        Note: exempting csrf here since phenotips doesn't have this support
    """
    project_name = request.session['current_project_id']
    project_phenotips_uname, project_phenotips_pwd = get_uname_pwd_for_project(project_name)
    try:
        curr_session = pickle.loads(request.session['current_phenotips_session'])
        url, parameters = __aggregate_url_parameters(request)
        response = curr_session.get(url, data=request.GET)
        http_response = HttpResponse(response.content)
        for header in response.headers.keys():
            if header != 'connection' and header != 'Transfer-Encoding':  # these hop-by-hop headers are not allowed by Django
                http_response[header] = response.headers[header]
        return http_response
    except Exception as e:
        print 'proxy get error:', e
        logger.error('phenotips.views:' + str(e))
        raise Http404


def __aggregate_url_parameters(request):
    """
        Given a request object,and base URL aggregates and returns a reconstructed URL
    """
    try:
        counter = 0
        parameters = {}
        url = settings.PHENOPTIPS_BASE_URL + request.path
        if len(request.GET) > 0:
            url += '?'
            for param, val in request.GET.iteritems():
                if param == 'xredirect':
                    val = val.replace('/', '%2F')
                    val = val.replace('=', '%3D')
                    val = val.replace('&', '%26')
                url += param + '=' + val
                parameters[param] = val
                if counter < len(request.GET) - 1:
                    url += '&'
                counter += 1
        return url, parameters
    except Exception as e:
        print 'url parameter aggregation error:', e
        raise


@csrf_exempt
@log_request('proxy_post')
@login_required
def proxy_post(request):
    """
        To act as a proxy for POST requests from Phenotips
        note: exempting csrf here since phenotips doesn't have this support
    """
    try:
        # print type(pickle.loads(request.session['current_phenotips_session']))
        # re-construct proxy-ed URL again
        url, parameters = __aggregate_url_parameters(request)
        project_name = request.session['current_project_id']
        uname, pwd = get_uname_pwd_for_project(project_name)
        curr_session = pickle.loads(request.session['current_phenotips_session'])

        logger.info("===> POSTING to url: " + url)
        logger.info("===> DATA: " + str(dict(request.POST)))
        logger.info("===> SESSION - headers: " + str(curr_session.headers))
        logger.info("===> SESSION - cookies: " + str(curr_session.cookies))
        logger.info("===> SESSION - auth: " + str(curr_session.auth))
        import requests
        #response = requests.post(url, headers=curr_session.headers, cookies=curr_session.cookies, auth=curr_session.auth)
        response = curr_session.post(url, data=dict(request.POST))

        from requests_toolbelt.utils import dump
        data = dump.dump_all(response)
        logger.info("===> dump - original:\n" + data.decode('utf-8'))

        http_response = HttpResponse(response.content)
        for header in response.headers.keys():
            if header != 'connection' and header != 'Transfer-Encoding':  # these hop-by-hop headers are not allowed by Django
                http_response[header] = response.headers[header]
        # persist outside of PhenoTips db as well
        if len(request.POST) != 0:
            patient_id = request.session['current_patient_id']
            __process_sync_request_helper(patient_id,
                                          request.user,
                                          project_name,
                                          parameters,
                                          pickle.loads(request.session['current_phenotips_session'])
                                          )

        logger.info("===> original api - HTTP RESPONSE DICT: ")
        for k,v in http_response.__dict__.items():
            logger.info("===> %s: %s" % (k,v))

        return http_response
    except Exception as e:
        print 'proxy post error:', e
        logger.error('phenotips.views:' + str(e))
        raise Http404


def __process_sync_request_helper(patient_id, xbrowse_user, project_name, url_parameters, curr_session):
    """
        Sync data of this user between xbrowse and phenotips. Persists the update in a 
        database for later searching and edit audits.
    """
    try:
        # first get the newest data via API call
        url = os.path.join(settings.PHENOPTIPS_BASE_URL, 'bin/get/PhenoTips/ExportPatient?id=' + patient_id)
        response = curr_session.get(url)
        updated_patient_record = response.json()
        settings.PHENOTIPS_EDIT_AUDIT.insert({
            'xbrowse_username': xbrowse_user.username,
            'xbrowse_user_email': xbrowse_user.email,
            'updated_patient_record': updated_patient_record,
            'project_name': project_name,
            'patient_id': patient_id,
            'url_parameters': parameters,
            'time': datetime.datetime.now()
        })        
    except Exception as e:
        sys.stderr.write('phenotips.views:' + str(e))

    try:
        external_id = updated_patient_record['external_id']
        i = Individual.objects.get(phenotips_id = external_id)
        i.phenotips_data = json.dumps(updated_patient_record)
        i.save()
    except Exception as e:
        sys.stderr.write('error while saving to db:' + str(e))




@log_request('upload_phenotips_page')
@login_required
def phenotypes_upload_page(request, project_id):
    """
    To help upload phenotips data from other PhenoTips instances
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    return render(request, 'phenotypes/upload_phenotypes.html',{})


@log_request('insert_individual_into_phenotips')
@login_required
def insert_individual_into_phenotips(request, eid,project_id):
    """
    """
    project = get_object_or_404(Project, project_id=project_id)
    print dir(project)
    if not project.can_view(request.user):
        raise PermissionDenied
    print eid
    phenotype_data = request.POST.get("patient_data","")
    return JSONResponse({'phenotype_data': phenotype_data})