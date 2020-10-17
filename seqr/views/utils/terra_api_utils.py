# This module provides python bindings for the AnVIL Terra API.

import json
import logging
import time

from urllib.parse import urljoin

from social_django.utils import load_strategy

from google.auth.transport.requests import AuthorizedSession
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

    def get(self, methcall, headers=None, root_url=None, **kwargs):
        """
        Call Terra API with HTTP GET method with an authentication header.

        Args:
            methcall: A string of API path (start right after the domain name without leading slash (/)
            headers (dict): Include additional headers as key-value pairs
            root_url: the url up to the domain name ending with a slash (/)
            kwargs: other parameters for the HTTP call, e.g. queries.
        Return:
            HTTP response
        """
        url, headers = _get_call_args(methcall, headers, root_url)
        r = super(AnvilSession, self).get(url, headers = headers, **kwargs)
        logger.info('GET {} {} {}'.format(url, r.status_code, len(r.text)))
        return r

    def post(self, methcall, headers=None, root_url=None, **kwargs):
        """See the __get() method."""
        url, headers = _get_call_args(methcall, headers, root_url)
        r = super(AnvilSession, self).post(url, headers = headers, **kwargs)
        logger.info('POST {} {} {}'.format(url, r.status_code, len(r.text)))
        return r

    def put(self, methcall, headers=None, root_url=None, **kwargs):
        """See the __get() method."""
        url, headers = _get_call_args(methcall, headers, root_url)
        r = super(AnvilSession, self).put(url, headers = headers, **kwargs)
        logger.info('PUT {} {} {}'.format(url, r.status_code, len(r.text)))
        return r

    def delete(self, methcall, headers=None, root_url=None):
        """See the __get() method."""
        url, headers = _get_call_args(methcall, headers, root_url)
        r = super(AnvilSession, self).delete(url, headers = headers)
        logger.info('DELETE {} {} {}'.format(url, r.status_code, len(r.text)))
        return r

    def get_billing_projects(self):
        """
        Get activation information for the logged-in user.

        :returns a list of billing project dictionary
        """
        r = self.get("api/profile/billing")
        if r.status_code != 200:
            raise TerraAPIException(
                'Error: called Terra API "api/profile/billing" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def get_anvil_profile(self):
        """Get activation information for the logged-in user."""
        r = self.get("register")
        if r.status_code != 200:
            raise TerraAPIException(
                'Error: called Terra API "register" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def list_workspaces(self, fields=None):
        """
        Get all the workspaces accessible by the logged-in user.

        Args:
        fields (str): a comma-delimited list of values that limits the
            response payload to include only those keys and exclude other
            keys (e.g., to include {"workspace": {"attributes": {...}}},
            specify "workspace.attributes").
        """
        if fields is None:
            r = self.get("api/workspaces")
        else:
            r = self.get("api/workspaces", params = {"fields": fields})
        if r.status_code != 200:
            raise TerraAPIException(
                'Error: called Terra API "api/workspaces" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def get_workspace_acl(self, workspace):
        """
        Request FireCloud access control list for workspace.

        Args:
            workspace (str): Workspace name in the format of 'namespace/workspace_name'
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
        """
        workspace = workspace.split('/') if workspace else ''
        if len(workspace) != 2:
            return {}
        uri = "api/workspaces/{0}/{1}/acl".format(workspace[0], workspace[1])
        r = self.get(uri)
        if r.status_code != 200:
            raise TerraAPIException(
                'Error: called Terra API "{}" got status: {} with a reason: {}'.format(uri, r.status_code, r.reason))
        return json.loads(r.text)['acl']


class AnvilSessionStore(object):
    service_account_session = AnvilSession(service_account_info = GOOGLE_SERVICE_ACCOUNT_INFO, scopes = SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE)
    sessions = {}

    def get_session(self, user=None):
        if user is None:
            return self.service_account_session
        social = user.social_auth.filter(provider = 'google-oauth2')
        if not social:
            return
        social = social.first()
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


anvilSessionStore = AnvilSessionStore()
