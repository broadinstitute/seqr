"""
seqr integrates with the `PhenoTips <http://phenotips.org>`_ UI so that users can enter
detailed phenotype information for individuals.
The PhenoTips server is installed locally so that it's not visible to the outside network, and
seqr then acts as a proxy for all HTTP requests between the PhenoTips web-based UI (which is
running in users' browser), and the PhenoTips server (running on the internal network).

This proxy setup allows seqr to check authentication and authorization before allowing users to
access patients in PhenoTips, and is similar to how seqr manages access to the SQL database and
other internal systems.

This module implements the proxy functionality + methods for making requests to PhenoTips HTTP APIs.

PhenoTips API docs are at:

https://phenotips.org/DevGuide/API
https://phenotips.org/DevGuide/RESTfulAPI
https://phenotips.org/DevGuide/PermissionsRESTfulAPI
"""

import json
import logging
import re
import requests

import settings

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from reference_data.models import HumanPhenotypeOntology
from seqr.model_utils import update_seqr_model
from seqr.models import Project, CAN_EDIT, CAN_VIEW, Individual
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.permissions_utils import check_permissions
from seqr.views.utils.proxy_request_utils import proxy_request

logger = logging.getLogger(__name__)

PHENOTIPS_QUICK_SAVE_URL_REGEX = "/bin/preview/data/(P[0-9]{1,20})"

DO_NOT_PROXY_URL_KEYWORDS = [
    '/delete',
    '/logout',
    '/login',
    '/admin',
    '/CreatePatientRecord',
    '/bin/PatientAccessRightsManagement',
    '/ForgotUsername',
    '/ForgotPassword',
]


def create_patient(project, individual):
    """Create a new PhenoTips patient record with the given patient id.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Raises:
        PhenotipsException: if unable to create patient record
    """

    url = '/rest/patients'
    headers = {"Content-Type": "application/json"}
    data = json.dumps({'external_id': individual.guid})
    auth_tuple = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id)

    response_items = _make_api_call('POST', url, auth_tuple=auth_tuple, http_headers=headers, data=data, expected_status_code=201, parse_json_resonse=False)
    patient_id = response_items['Location'].split('/')[-1]

    username_read_only, _ = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    add_user_to_patient(username_read_only, patient_id, allow_edit=False)
    logger.info("Added PhenoTips user {username} to {patient_id}".format(username=username_read_only, patient_id=patient_id))

    return patient_id


def get_patient_data(project, individual):
    """Retrieves patient data from PhenoTips and returns a json obj.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Returns:
        dict: json dictionary containing all PhenoTips information for this patient
    Raises:
        PhenotipsException: if unable to retrieve data from PhenoTips
    """
    url = _phenotips_patient_url(individual)

    auth_tuple = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id)
    return _make_api_call('GET', url, auth_tuple=auth_tuple, verbose=False)


def update_patient_data(project, individual, patient_json):
    """Updates patient data in PhenoTips to the values in patient_json.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
        patient_json (dict): phenotips patient record like the object returned by get_patient_data(..).
    Raises:
        PhenotipsException: if api call fails
    """
    if not patient_json:
        raise ValueError("patient_json arg is empty")

    url = _phenotips_patient_url(individual)
    patient_json_string = json.dumps(patient_json)

    auth_tuple = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    result = _make_api_call('PUT', url, data=patient_json_string, auth_tuple=auth_tuple, expected_status_code=204)

    return result


def delete_patient(project, individual):
    """Deletes patient from PhenoTips for the given patient_id.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Raises:
        PhenotipsException: if api call fails
    """

    url = _phenotips_patient_url(individual)

    auth_tuple = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    return _make_api_call('DELETE', url, auth_tuple=auth_tuple, expected_status_code=204)


def _phenotips_patient_url(individual):
    if individual.phenotips_patient_id:
        return '/rest/patients/{0}'.format(individual.phenotips_patient_id)
    else:
        return '/rest/patients/eid/{0}'.format(individual.guid)


def update_patient_field_value(project, individual, field_name, field_value):
    """ Utility method for updating one field in the patient record, while keeping other fields
    the same. For field descriptions, see https://phenotips.org/DevGuide/JSONExport1.3

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
        field_name (string): PhenoTips patient field name (eg. "family_history").
        field_value (string or dict): PhenoTips HPO terms.
    Raises:
        PhenotipsException: if api call fails
    """
    if field_name not in set([
        "allergies",
        "apgar",
        "clinicalStatus",
        "date_of_birth",
        "date_of_death",
        "disorders",
        "ethnicity",
        "external_id",
        "family_history",
        "features",
        "genes",
        "global_age_of_onset",
        "global_mode_of_inheritance",
        "life_status",
        "nonstandard_features",
        "notes",
        "prenatal_perinatal_history",
        "sex",
        "solved",
        "specificity",
        "variants",
    ]):
        raise ValueError("Unexpected field_name: %s" % (field_name, ))

    patient_json = get_patient_data(project, individual)
    patient_json[field_name] = field_value

    update_patient_data(project, individual, patient_json)


def set_patient_hpo_terms(project, individual, hpo_terms_present=[], hpo_terms_absent=[], final_diagnosis_mim_ids=[]):
    """Utility method for specifying a list of HPO IDs for a patient.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
        hpo_terms_present (list): list of HPO IDs for phenotypes present in this patient (eg. ["HP:00012345", "HP:0012346", ...])
        hpo_terms_absent (list): list of HPO IDs for phenotypes not present in this patient (eg. ["HP:00012345", "HP:0012346", ...])
        final_diagnosis_mim_ids (int): one or more MIM Ids (eg. [105650, ..])
    Raises:
        PhenotipsException: if api call fails
    """

    if hpo_terms_present or hpo_terms_absent:
        features_value = [{"id": hpo_term, "observed": "yes", "type": "phenotype"} for hpo_term in hpo_terms_present]
        features_value += [{"id": hpo_term, "observed": "no", "type": "phenotype"} for hpo_term in hpo_terms_absent]
        update_patient_field_value(project, individual, "features", features_value)

    if final_diagnosis_mim_ids:
        omim_disorders = []
        for mim_id in final_diagnosis_mim_ids:
            if int(mim_id) < 100000:
                raise ValueError("Invalid final_diagnosis_mim_id: %s. Expected a 6-digit number." % str(mim_id))
            omim_disorders.append({'id': 'MIM:%s' % mim_id})
        update_patient_field_value(project, individual, "disorders", omim_disorders)

    patient_json = get_patient_data(project, individual)
    _update_individual_phenotips_data(individual, patient_json)



def add_user_to_patient(username, patient_id, allow_edit=True):
    """Grant a PhenoTips user access to the given patient.

    Args:
        username (string): PhenoTips username to grant access to.
        patient_id (string): PhenoTips internal patient id.
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        'collaborator': 'XWiki.' + str(username),
        'patient': patient_id,
        'accessLevel': 'edit' if allow_edit else 'view',
        'xaction': 'update',
        'submit': 'Update'
    }

    url = '/bin/get/PhenoTips/PatientAccessRightsManagement?outputSyntax=plain'
    _make_api_call(
        'POST',
        url,
        http_headers=headers,
        data=data,
        auth_tuple=(settings.PHENOTIPS_ADMIN_UNAME, settings.PHENOTIPS_ADMIN_PWD),
        expected_status_code=204,
        parse_json_resonse=False,
    )


def create_phenotips_user(username, password):
    """Creates a new user in PhenoTips"""

    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    data = { 'parent': 'XWiki.XWikiUsers' }

    url = '/rest/wikis/xwiki/spaces/XWiki/pages/{username}'.format(username=username)
    _make_api_call(
        'PUT',
        url,
        http_headers=headers,
        data=data,
        auth_tuple=(settings.PHENOTIPS_ADMIN_UNAME, settings.PHENOTIPS_ADMIN_PWD),
        parse_json_resonse=False,
        expected_status_code=[201, 202],
    )

    data = {
        'className': 'XWiki.XWikiUsers',
        'property#password': password,
        #'property#first_name': first_name,
        #'property#last_name': last_name,
        #'property#email': email_address,
    }

    url = '/rest/wikis/xwiki/spaces/XWiki/pages/{username}/objects'.format(username=username)
    return _make_api_call(
        'POST',
        url,
        data=data,
        auth_tuple=(settings.PHENOTIPS_ADMIN_UNAME, settings.PHENOTIPS_ADMIN_PWD),
        parse_json_resonse=False,
        expected_status_code=201,
    )


@login_required
@csrf_exempt
def phenotips_pdf_handler(request, project_guid, patient_id):
    """Requests the PhenoTips PDF for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        patient_id (string): PhenoTips internal patient id
    """

    url = "/bin/export/data/{patient_id}?format=pdf&pdfcover=0&pdftoc=0&pdftemplate=PhenoTips.PatientSheetCode".format(patient_id=patient_id)
    project = Project.objects.get(guid=project_guid)

    check_permissions(project, request.user, CAN_VIEW)

    auth_tuple = _get_phenotips_username_and_password(request.user, project, permissions_level=CAN_VIEW)

    return proxy_request(request, url, headers={}, auth_tuple=auth_tuple, host=settings.PHENOTIPS_SERVER)


@login_required
@csrf_exempt
def phenotips_edit_handler(request, project_guid, patient_id):
    """Request the PhenoTips Edit page for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        patient_id (string): PhenoTips internal patient id
    """

    # query string forwarding needed for PedigreeEditor button
    query_string = request.META["QUERY_STRING"]
    url = "/bin/edit/data/{patient_id}?{query_string}".format(patient_id=patient_id, query_string=query_string)

    project = Project.objects.get(guid=project_guid)

    check_permissions(project, request.user, CAN_EDIT)

    auth_tuple = _get_phenotips_username_and_password(request.user, project, permissions_level=CAN_EDIT)

    return proxy_request(request, url, headers={}, auth_tuple=auth_tuple, host=settings.PHENOTIPS_SERVER)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def proxy_to_phenotips_handler(request):
    """This django view accepts GET and POST requests and forwards them to PhenoTips"""

    url = request.get_full_path()
    if any([k for k in DO_NOT_PROXY_URL_KEYWORDS if k.lower() in url.lower()]):
        logger.warn("Blocked proxy url: " + str(url))
        return HttpResponse(status=204)
    logger.info("Proxying url: " + str(url))

    #if 'current_phenotips_session' not in request.session:
    #    phenotips_session = requests.Session()
    #    request.session['current_phenotips_session'] = pickle.dumps(phenotips_session)
    #else:
    #    phenotips_session = pickle.loads(request.session['current_phenotips_session'])

    # Some PhenoTips endpoints that use HTTP redirects lose the phenotips JSESSION auth cookie
    # along the way, and don't proxy correctly. Using a Session object as below to store the cookies
    # provides a work-around.
    phenotips_session = requests.Session()
    for key, value in request.COOKIES.items():
        phenotips_session.cookies.set(key, value)

    http_response = proxy_request(request, url, data=request.body, session=phenotips_session,
                                  host=settings.PHENOTIPS_SERVER, filter_request_headers=True)

    # if this is the 'Quick Save' request, also save a copy of phenotips data in the seqr SQL db.
    match = re.match(PHENOTIPS_QUICK_SAVE_URL_REGEX, url)
    if match:
        _handle_phenotips_save_request(request, patient_id=match.group(1))

    return http_response


def _make_api_call(
        method,
        url,
        http_headers={},
        data=None,
        auth_tuple=None,
        expected_status_code=200,
        parse_json_resonse=True,
        verbose=False):
    """Utility method for making an API call and then parsing & returning the json response.

    Args:
        method (string): 'GET' or 'POST'
        url (string): url path, starting with '/' (eg. '/bin/edit/data/P0000001')
        data (string): request body - used for POST, PUT, and other such requests.
        auth_tuple (tuple): ("username", "password") pair
        expected_status_code (int or list): expected server response code
        parse_json_resonse (bool): whether to parse and return the json response
        verbose (bool): whether to print details about the request & response
    Returns:
        json object or None if response content is empty
    """

    try:
        response = proxy_request(None, url, headers=http_headers, method=method, scheme='http', data=data,
                                 auth_tuple=auth_tuple, host=settings.PHENOTIPS_SERVER, verbose=verbose)
    except requests.exceptions.RequestException as e:
        raise PhenotipsException(e.message)
    if (isinstance(expected_status_code, int) and response.status_code != expected_status_code) or (
        isinstance(expected_status_code, list) and response.status_code not in expected_status_code):
        raise PhenotipsException("Unable to retrieve %s. response code = %s: %s" % (
            url, response.status_code, response.reason_phrase))

    if parse_json_resonse:
        if not response.content:
            return {}

        try:
            return json.loads(response.content)
        except ValueError as e:
            logger.error("Unable to parse PhenoTips response for %s request to %s" % (method, url))
            raise PhenotipsException("Unable to parse response for %s:\n%s" % (url, e))
    else:
        return dict(response.items())


def _handle_phenotips_save_request(request, patient_id):
    """Update the seqr SQL database record for this patient with the just-saved phenotype data."""

    url = '/rest/patients/%s' % patient_id

    cookie_header = request.META.get('HTTP_COOKIE')
    http_headers = {'Cookie': cookie_header} if cookie_header else {}
    response = proxy_request(request, url, headers=http_headers, method='GET', scheme='http', host=settings.PHENOTIPS_SERVER)
    if response.status_code != 200:
        logger.error("ERROR: unable to retrieve patient json. %s %s %s" % (
            url, response.status_code, response.reason_phrase))
        return

    patient_json = json.loads(response.content)

    try:
        if patient_json.get('external_id'):
            # prefer to use the external id for legacy reasons: some projects shared phenotips
            # records by sharing the phenotips internal id, so in rare cases, the
            # Individual.objects.get(phenotips_patient_id=...) may match multiple Individual records
            individual = Individual.objects.get(phenotips_eid=patient_json['external_id'])
        else:
            individual = Individual.objects.get(phenotips_patient_id=patient_json['id'])

    except ObjectDoesNotExist as e:
        logger.error("ERROR: PhenoTips patient id %s not found in seqr Individuals." % patient_json['id'])
        return

    _update_individual_phenotips_data(individual, patient_json)


def _update_individual_phenotips_data(individual, patient_json):
    """Process and store the given patient_json in the given Individual model.

    Args:
        individual (Individual): Django Individual model
        patient_json (json): json dict representing the patient record in PhenoTips
    """

    # for each HPO term, get the top level HPO category (eg. Musculoskeletal)
    for feature in patient_json.get('features', []):
        hpo_id = feature['id']
        try:
            feature['category'] = HumanPhenotypeOntology.objects.get(hpo_id=hpo_id).category_id
        except ObjectDoesNotExist:
            logger.error("ERROR: PhenoTips HPO id %s not found in seqr HumanPhenotypeOntology table." % hpo_id)

    update_seqr_model(
        individual,
        phenotips_data=json.dumps(patient_json),
        phenotips_patient_id=patient_json['id'],        # phenotips internal id
        phenotips_eid=patient_json.get('external_id'))  # phenotips external id


def _get_phenotips_uname_and_pwd_for_project(phenotips_user_id, read_only=False):
    """Return the PhenoTips username and password for this seqr project"""
    if not phenotips_user_id:
        raise ValueError("Invalid phenotips_user_id: " + str(phenotips_user_id))

    uname = phenotips_user_id + ('_view' if read_only else '')
    pwd = phenotips_user_id + phenotips_user_id

    return uname, pwd


def _get_phenotips_username_and_password(user, project, permissions_level):
    """Checks if user has permission to access the given project, and raises an exception if not.

    Args:
        user (User): the django user object
        project(Model): Project model
        permissions_level (string): 'edit' or 'view'
    Raises:
        PermissionDenied: if user doesn't have permission to access this project.
    Returns:
        2-tuple: PhenoTips username, password that can be used to access patients in this project.
    """
    if permissions_level == CAN_EDIT:
        uname, pwd = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    elif permissions_level == CAN_VIEW:
        uname, pwd = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    else:
        raise ValueError("Unexpected auth_permissions value: %s" % permissions_level)

    auth_tuple = (uname, pwd)

    return auth_tuple


class PhenotipsException(Exception):
    pass
