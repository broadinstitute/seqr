import json
import logging
import requests

import settings

from seqr.views.utils.proxy_request_utils import proxy_request

logger = logging.getLogger(__name__)


def delete_phenotips_patient(project, individual):
    """Deletes patient from PhenoTips for the given patient_id.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Raises:
        PhenotipsException: if api call fails
    """
    if phenotips_patient_exists(individual):
        url = phenotips_patient_url(individual)
        auth_tuple = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
        return make_phenotips_api_call('DELETE', url, auth_tuple=auth_tuple, expected_status_code=204)


def phenotips_patient_url(individual):
    if individual.phenotips_patient_id:
        return '/rest/patients/{0}'.format(individual.phenotips_patient_id)
    else:
        return '/rest/patients/eid/{0}'.format(individual.phenotips_eid)


def phenotips_patient_exists(individual):
    return individual.phenotips_patient_id or individual.phenotips_eid


def create_phenotips_user(username, password):
    """Creates a new user in PhenoTips"""

    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    data = { 'parent': 'XWiki.XWikiUsers' }

    url = '/rest/wikis/xwiki/spaces/XWiki/pages/{username}'.format(username=username)
    make_phenotips_api_call(
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
    return make_phenotips_api_call(
        'POST',
        url,
        data=data,
        auth_tuple=(settings.PHENOTIPS_ADMIN_UNAME, settings.PHENOTIPS_ADMIN_PWD),
        parse_json_resonse=False,
        expected_status_code=201,
    )


def make_phenotips_api_call(
        method,
        url,
        http_headers=None,
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
        response = proxy_request(None, url, headers=http_headers or {}, method=method, scheme='http', data=data,
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


def get_phenotips_uname_and_pwd_for_project(phenotips_user_id, read_only=False):
    """Return the PhenoTips username and password for this seqr project"""
    if not phenotips_user_id:
        raise ValueError("Invalid phenotips_user_id: " + str(phenotips_user_id))

    uname = phenotips_user_id + ('_view' if read_only else '')
    pwd = phenotips_user_id + phenotips_user_id

    return uname, pwd


class PhenotipsException(Exception):
    pass
