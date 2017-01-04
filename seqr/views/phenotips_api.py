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

PhenoTips API docs are at: https://phenotips.org/DevGuide/RESTfulAPI
"""

import json
import logging
import re
import requests
import settings

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

from seqr.models import Project, CAN_EDIT, CAN_VIEW


logger = logging.getLogger(__name__)


HTTP_HOP_BY_HOP_HEADERS = {
    k.lower() for k in ['Connection', 'Keep-Alive', 'Proxy-Authenticate', 'Proxy-Authorization', 'TE', 'Trailers', 'Transfer-Encoding', 'Upgrade',]
}
PHENOTIPS_QUICK_SAVE_URL_REGEX = "/preview/data/(P[0-9]{1,20})"


class PhenotipsException(Exception):
    pass


def get_patient_data(project, patient_id, is_external_id=False):
    """Retrieves patient data from PhenoTips and returns a json obj.

    Args:
        project (Model): used to retrieve PhenoTips credentials
        patient_id (string): PhenoTips patient id (either internal eg. "P000001" or external eg. "NA12878")
        is_external_id (bool): whether the provided id is an external id
    Returns:
        dict: json dictionary containing all PhenoTips information for this patient
    Raises:
        PhenotipsException: if unable to retrieve data from PhenoTips
    """
    if is_external_id:
        url = '/rest/patients/eid/%(patient_id)s' % locals()
    else:
        url = '/rest/patients/%(patient_id)s' % locals()

    auth_tuple = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)

    response = _send_request_to_phenotips('GET', url, auth_tuple=auth_tuple)
    if response.status_code != 200:
        raise PhenotipsException("Unable to retrieve %s. response code = %s: %s" % (
            url, response.status_code, response.reason_phrase))

    return json.loads(response.content)


@login_required
@csrf_exempt
def phenotips_view_patient_pdf(request, project_guid, patient_id):
    """Requests the PhenoTips PDF for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        patient_id (string): PhenoTips internal patient id
    """

    url = "/bin/export/data/%(patient_id)s?format=pdf&pdfcover=0&pdftoc=0&pdftemplate=PhenoTips.PatientSheetCode" % locals()
    project = Project.objects.get(guid=project_guid)
    permissions_level = 'view'

    auth_tuple = _check_user_permissions(request.user, project, permissions_level)

    return _send_request_to_phenotips('GET', url, auth_tuple=auth_tuple)


@login_required
@csrf_exempt
def phenotips_edit_patient(request, project_guid, patient_id):
    """Request the PhenoTips Edit page for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        patient_id (string): PhenoTips internal patient id
    """
    url = "/bin/edit/data/%(patient_id)s" % locals()
    project = Project.objects.get(guid=project_guid)
    permissions_level = 'edit'

    auth_tuple = _check_user_permissions(request.user, project, permissions_level)

    return _send_request_to_phenotips('GET', url, auth_tuple=auth_tuple)


@login_required
@csrf_exempt
def proxy_to_phenotips(request):
    """This django view accepts GET and POST requests and forwards them to PhenoTips

    *NOTE*: The initial request from a seqr page to a PhenoTips url must include `auth_project_guid` and
    `auth_permissions` HTTP parameters.
    These are used to login to PhenoTips while forwarding the request. If they're not provided, the
    code assumes authentication to PhenoTips was done on a previous call (if it wasn't,
    PhenoTips will reject this request and redirect to its login page).

    Example request:

    ```GET https://seqr.broadinstitute.org/bin/edit/data/P0000001?auth_project_guid=20160503_ASDFG_1kg&auth_permissions=edit```


    Args:
        auth_project_guid (string): seqr project GUID
        auth_permissions (string): 'edit' or 'view'
    """

    # get query parameters regardless of whether this is an HTTP GET or POST request
    query_dict = request.GET or request.POST

    # handle authentication if needed
    auth_tuple = None
    if 'auth_project_guid' in query_dict and 'auth_permissions' in query_dict:
        project_guid = query_dict['auth_project_guid']
        permissions_level = query_dict['auth_permissions']

        project = Project.objects.get(guid=project_guid)

        auth_tuple = _check_user_permissions(request.user, project, permissions_level)

    # forward the request to PhenoTips, and then the PhenoTips response back to seqr
    url = request.get_full_path()
    http_headers = _convert_django_META_to_http_headers(request.META)
    request_params = list(_convert_django_query_dict_to_tuples(query_dict))
    http_response = _send_request_to_phenotips(request.method, url, http_headers, request_params, auth_tuple)

    # if this is the 'Quick Save' request, also save a copy of the data in the seqr SQL db.
    match = re.match(PHENOTIPS_QUICK_SAVE_URL_REGEX, url)
    if match:
        _handle_phenotips_save_request(request, patient_id = match.group(1))

    return http_response


def _send_request_to_phenotips(method, url, http_headers=None, request_params=None, auth_tuple=None):
    """Send an HTTP request to a PhenoTips server.
    (see PhenoTips API docs: https://phenotips.org/DevGuide/RESTfulAPI)

    Args:
        method (string): 'GET' or 'POST'
        url (string): url path (eg. '/bin/edit/data/P0000001')
        http_headers: (dict): HTTP headers to send
        request_params (dict): HTTP query params to include in the URL of a GET request, or the
            body of a POST request
        auth_tuple: ("username", "password") pair

    Returns:
        HttpResponse from the PhenoTips server.
    """

    full_url = "http://%s:%s%s" % (settings.PHENOTIPS_HOST, settings.PHENOTIPS_PORT, url)
    if method == "GET":
        response = requests.get(full_url, headers=http_headers, data=request_params, auth=auth_tuple)
    elif method == "POST":
        response = requests.post(full_url, headers=http_headers, data=request_params, auth=auth_tuple)
    else:
        raise ValueError("Unexpected HTTP method: %s. %s" % (method, url))

    http_response = HttpResponse(
        content=response.content,
        status=response.status_code,
        reason=response.reason,
        charset=response.encoding
    )

    for header_key, header_value in response.headers.items():
        if header_key.lower() not in HTTP_HOP_BY_HOP_HEADERS:
            http_response[header_key] = header_value

    return http_response


def _handle_phenotips_save_request(request, patient_id):
    """Update the seqr SQL database record for this patient with the just-saved phenotype data."""
    url = '/rest/patients/%s' % patient_id
    http_headers = _convert_django_META_to_http_headers(request.META)
    response = _send_request_to_phenotips('GET', url, http_headers=http_headers)
    if response.status_code != 200:
        logger.error("ERROR: unable to retrieve patient json. %s %s %s" % (
            url, response.status_code, response.reason_phrase))
        return

    patient_data = json.loads(response.content)

    from pprint import pprint
    pprint(patient_data)

    logger.info("TODO: save data: %s" % (patient_data, ))
    # for each record, get the top level HPO category


def _get_phenotips_uname_and_pwd_for_project(phenotips_user_id, read_only=False):
    """Return the PhenoTips username and password for this seqr project"""

    uname = phenotips_user_id + ('_view' if read_only else '')
    pwd = phenotips_user_id + phenotips_user_id

    return uname, pwd


def _check_user_permissions(user, project, permissions_level):
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
    if permissions_level == "edit":
        if not user.has_perm(CAN_EDIT, project):
            raise PermissionDenied("%s does not have EDIT permissions for %s" % (user, project))
        uname, pwd = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    elif permissions_level == "view":
        if not user.has_perm(CAN_VIEW, project):
            raise PermissionDenied("%s does not have VIEW permissions for %s" % (user, project))
        uname, pwd = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    else:
        raise ValueError("Unexpected auth_permissions value: %s" % permissions_level)

    auth_tuple = (uname, pwd)

    return auth_tuple


def _convert_django_META_to_http_headers(meta_dict):
    """Converts django request.META dictionary into a dictionary of HTTP headers"""
    def convert_key(key):
        key = key.replace("HTTP_", "")
        tokens = key.split("_")
        capitalized_tokens = map(lambda x: x.capitalize(), tokens)
        return "-".join(capitalized_tokens)

    http_headers = {
        convert_key(key): value
        for key, value in meta_dict.items()
        if key.startswith("HTTP_")
    }

    return http_headers


def _convert_django_query_dict_to_tuples(query_dict):
    """HTTP GET and POST requests can have duplicate keys - for example: a=1&a=2&c=3.
    The django GET and POST QueryDict represents these as a dictionary of lists: {'a': [1, 2], 'c': [3]}
    and this method takes this dictionary and converts it to a list of tuples: [(a, 1), (a, 2), (c, 3)]
    which can be used to pass GET or POST parameters to the requests module.
    """
    for key, list_value in query_dict.iterlists():
        for value in list_value:
            yield (key, value)
