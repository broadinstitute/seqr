# This module provides python bindings for the AnVIL Terra API.

import json
import logging
import time

from urllib.parse import urljoin

from social_django.utils import load_strategy

from google.auth.transport.requests import AuthorizedSession
from google.auth.transport import DEFAULT_REFRESH_STATUS_CODES
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from settings import SEQR_VERSION, TERRA_API_ROOT_URL, GOOGLE_SERVICE_ACCOUNT_INFO, SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

logger = logging.getLogger(__name__)


class TerraAPIException(Exception):
    """For exceptions happen in Terra API calls."""
    pass


def _get_call_args(methcall, headers=None, root_url=None):
    if headers is None:
        headers = {"User-Agent": SEQR_USER_AGENT}
    if root_url is None:
        root_url = TERRA_API_ROOT_URL
    url = urljoin(root_url, methcall)
    return url, headers


class AnvilSession(AuthorizedSession):

    def __init__(self, credentials=None, service_account_info=None, scopes=None):
        """
        Create an AnVIL session for a user account if credentials are provided, otherwise create one for the service account

        :param credentials: User credentials
        :param service_account_info: service account secrects
        :param scopes: scopes of the access privilege of the session
        """
        if credentials is None:
            credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes = scopes)
        super(AnvilSession, self).__init__(credentials)

    def _make_request(self, method, path, headers, root_url, **kwargs):
        url, headers = _get_call_args(path, headers, root_url)
        request_func = getattr(super(AnvilSession, self), method)
        r = request_func(url, headers = headers, **kwargs)
        if r.status_code != 200:
            logger.info('{} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text)))
            raise TerraAPIException('Error: called Terra API "{}" got status: {} with a reason: {}'.format(
                path, r.status_code, r.reason))
        return r

    def get(self, path, headers=None, root_url=None, **kwargs):
        """
        Call Terra API with HTTP GET method with an authentication header.

        Args:
            path: A string of API path (start right after the domain name without leading slash (/)
            headers (dict): Include additional headers as key-value pairs
            root_url: the url up to the domain name ending with a slash (/)
            kwargs: other parameters for the HTTP call, e.g. queries.
        Return:
            HTTP response
        """
        return self._make_request('get', path, headers, root_url, **kwargs)

    def post(self, path, headers=None, root_url=None, **kwargs):
        """See the __get() method."""
        return self._make_request('post', path, headers, root_url, **kwargs)

    def put(self, path, headers=None, root_url=None, **kwargs):
        """See the __get() method."""
        return self._make_request('put', path, headers, root_url, **kwargs)

    def delete(self, path, headers=None, root_url=None):
        """See the __get() method."""
        return self._make_request('delete', path, headers, root_url)


def get_anvil_billing_projects(user):
    """
    Get activation information for the logged-in user.

    Args:
        user (User model): who's credentials will be used to access AnVIL

    :returns a list of billing project dictionary
    """
    session = _anvil_session_store.get_session(user)
    r = session.get("api/profile/billing")
    if r.status_code != 200:
        raise TerraAPIException(
            'Error: called Terra API "api/profile/billing" got status: {} with a reason: {}'.format(r.status_code, r.reason))
    return json.loads(r.text)


def get_anvil_profile(user):
    """Get activation information for the logged-in user.

    Args:
        user (User model): who's credentials will be used to access AnVIL
    """
    session = _anvil_session_store.get_session(user)
    r = session.get("register")
    if r.status_code != 200:
        raise TerraAPIException(
            'Error: called Terra API "register" got status: {} with a reason: {}'.format(r.status_code, r.reason))
    return json.loads(r.text)


def list_anvil_workspaces(user, fields=None):
    """
    Get all the workspaces accessible by the logged-in user.

    Args:
    user (User model): who's credentials will be used to access AnVIL
    fields (str): a comma-delimited list of values that limits the
        response payload to include only those keys and exclude other
        keys (e.g., to include {"workspace": {"attributes": {...}}},
        specify "workspace.attributes").
    """
    session = _anvil_session_store.get_session(user)
    params = {"fields": fields} if fields is not None else {}
    r = session.get("api/workspaces", params = params)
    if r.status_code != 200:
        raise TerraAPIException(
            'Error: called Terra API "api/workspaces" got status: {} with a reason: {}'.format(r.status_code, r.reason))
    return json.loads(r.text)


def get_anvil_workspace_acl(workspace_namespace, workspace_name):
    """
    Request FireCloud access control list for workspace.

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
    r = _anvil_session_store.service_account_session.get(uri)
    if r.status_code in DEFAULT_REFRESH_STATUS_CODES:  # has failed in refreshing the access code
        _anvil_session_store._service_account_session = None
        r = _anvil_session_store.service_account_session.get(uri)  # retry with the new access code
    if r.status_code != 200:
        raise TerraAPIException(
            'Error: called Terra API "{}" got status: {} with a reason: {}'.format(uri, r.status_code, r.reason))
    return json.loads(r.text)['acl']


def is_google_authenticated(user):
    return len(user.social_auth.filter(provider = 'google-oauth2'))>0


class AnvilSessionStore(object):
    sessions = {}

    def __init__(self):
        self._service_account_session = None

    @property
    def service_account_session(self):
        if not self._service_account_session:
            self._service_account_session = AnvilSession(service_account_info = GOOGLE_SERVICE_ACCOUNT_INFO,
                                                         scopes = SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE)
        return self._service_account_session

    def get_session(self, user):
        social = user.social_auth.get(provider = 'google-oauth2')
        if self.sessions.get(user.username):
            if (social.extra_data['auth_time'] + social.extra_data['expires'] - 10) <= int(time.time()):  # token expired or expiring?
                strategy = load_strategy()
                try:
                    social.refresh_token(strategy)
                except Exception as ee:
                    logger.info('Refresh token failed. {}'.format(str(ee)))
                    self.sessions.pop(user.username)
            else:
                # Todo: change to 'return self.sessions[user.username]' after whitelisted
                return self.service_account_session  # self.sessions[user.username]
        credentials = Credentials(token = social.extra_data['access_token'])
        session = AnvilSession(credentials = credentials)
        self.sessions.update({user.username: session})
        # Todo: change to 'return session' after whitelisted
        return self.service_account_session  # session


_anvil_session_store = AnvilSessionStore()
