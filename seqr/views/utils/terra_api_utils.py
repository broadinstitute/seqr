# This module provides python bindings for the AnVIL Terra API.

import json
import logging
import time
import requests

from urllib.parse import urljoin

from social_django.models import UserSocialAuth
from social_django.utils import load_strategy

from google.auth.transport.requests import AuthorizedSession
from google.auth.transport import DEFAULT_REFRESH_STATUS_CODES
from google.oauth2 import service_account

from settings import SEQR_VERSION, TERRA_API_ROOT_URL, GOOGLE_SERVICE_ACCOUNT_INFO, SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

logger = logging.getLogger(__name__)


class TerraAPIException(Exception):
    pass


def anvil_enabled():
    return bool(TERRA_API_ROOT_URL)


def is_google_authenticated(user):
    if not anvil_enabled():
        return False
    try:
        _ = user.social_auth.get(provider = 'google-oauth2')
    except UserSocialAuth.DoesNotExist:  # Exception happen when the user has never logged-in with Google
        return False
    return True


def _get_call_args(path, headers=None, root_url=None):
    if headers is None:
        headers = {"User-Agent": SEQR_USER_AGENT}
    headers.update({"accept": "application/json"})
    if root_url is None:
        root_url = TERRA_API_ROOT_URL
    url = urljoin(root_url, path)
    return url, headers


class ServiceAccountSession(AuthorizedSession):

    def __init__(self):
        """Init the session start time and avoid initializing the base class."""
        self.started_at = None

    def create_session(self):
        """Create a service account session."""
        credentials = service_account.Credentials.from_service_account_info(GOOGLE_SERVICE_ACCOUNT_INFO,
                                        scopes = SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE)
        super(ServiceAccountSession, self).__init__(credentials)
        self.started_at = time.time()

    def _make_request(self, method, path, headers, root_url, **kwargs):
        """Parameter "method" is string which can be "get", "post", or "delete"."""
        if self.started_at is None:
            self.create_session()
        url, headers = _get_call_args(path, headers, root_url)
        request_func = getattr(super(ServiceAccountSession, self), method)
        r = request_func(url, headers = headers, **kwargs)
        if r.status_code in DEFAULT_REFRESH_STATUS_CODES:  # has failed in refreshing the access code
            self.create_session()  # create a new service account session
            r = request_func(url, headers = headers, **kwargs)
        if r.status_code != 200:
            logger.info('{} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text)))
            raise TerraAPIException('Error: called Terra API "{}" got status: {} with a reason: {}'.format(
                path, r.status_code, r.reason))
        return json.loads(r.text)

    def get(self, path, headers=None, root_url=None, **kwargs):
        """Call Terra API with HTTP GET method with an authentication header.

        :param
            path: A string of API path (start right after the domain name without leading slash (/)
            headers (dict): Include additional headers as key-value pairs
            root_url: the url up to the domain name ending with a slash (/)
            kwargs: other parameters for the HTTP call, e.g. queries.
        :return
            HTTP response
        """
        return self._make_request('get', path, headers, root_url, **kwargs)


_service_account_session = ServiceAccountSession()


def sa_get_workspace_acl(workspace_namespace, workspace_name):
    """
    Requests AnVIL access control list for a workspace with a service account (sa).

    The workspace of AnVIL is identified by its namespace and name.

    Args:
        workspace_namespace (str): namespace (name of billing project) of the workspace
        workspace_name (str): the name of the workspace
    Returns:
        {
            "user1Email": {
              "accessLevel": "string",
              "pending": true,
              "canShare": true,
              "canCompute": true
            },
            "user2Email": {
              "accessLevel": "string",
              "pending": true,
              "canShare": true,
              "canCompute": true
            },
            "user3Email": {
              "accessLevel": "string",
              "pending": true,
              "canShare": true,
              "canCompute": true
            }
          }
          :param workspace_name:
          :param workspace_namespace:
    """
    uri = "api/workspaces/{0}/{1}/acl".format(workspace_namespace, workspace_name)
    r = _service_account_session.get(uri)
    return r.get('acl', {})


def _get_social_access_token(user):
    social = user.social_auth.get(provider = 'google-oauth2')
    if (social.extra_data['auth_time'] + social.extra_data['expires'] - 10) <= int(
            time.time()):  # token expired or expiring?
        strategy = load_strategy()
        try:
            social.refresh_token(strategy)
        except Exception as ee:
            logger.info('Refresh token failed. {}'.format(str(ee)))
            raise TerraAPIException('Refresh token failed. {}'.format(str(ee)))
    return social.extra_data['access_token']


def anvil_call(method, path, access_token, headers=None, root_url=None, **kwargs):
    url, headers = _get_call_args(path, headers, root_url)
    request_func = getattr(requests, method)
    headers.update({'Authorization': 'Bearer {}'.format(access_token)})
    r = request_func(url, headers=headers, **kwargs)

    if r.status_code != 200:
        logger.info('{} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text)))
        raise TerraAPIException('Error: called Terra API "{}" got status: {} with a reason: {}'.format(
            path, r.status_code, r.reason))
    return json.loads(r.text)


def _user_anvil_call(method, path, user, **kwargs):
    access_token = _get_social_access_token(user)
    return anvil_call(method, path, access_token, **kwargs)


def list_anvil_workspaces(user, fields=None):
    """Get all the workspaces accessible by the logged-in user.

    :param
    user (User model): who's credentials will be used to access AnVIL
    fields (str): a comma-delimited list of values that limits the
        response payload to include only those keys and exclude other
        keys (e.g., to include {"workspace": {"attributes": {...}}},
        specify "workspace.attributes").
    :return
    A list of workspaces that the user has access (OWNER, WRITER, or READER). Each of the workspace has
    the fields that specified by the 'fields' parameter or all the fields that AnVIL provides.
    """
    path = 'api/workspaces?fields={}'.format(fields) if fields else 'api/workspaces'
    return _user_anvil_call('get', path, user)
