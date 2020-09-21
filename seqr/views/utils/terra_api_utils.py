"""
This module provides python bindings for the AnVIL Terra API.
"""

import json
import logging

from urllib.parse import urljoin

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from settings import SEQR_VERSION, TERRA_API_CONFIG

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

scopes = ['https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/cloud-billing',
          'openid']

logger = logging.getLogger(__name__)


class TerraAPIException(Exception):
    """For exceptions happen in Terra API calls
    """
    pass


class AnvilSession:
    def __init__(self, credentials=None, service_account_secret="service_account.json", scopes=None):
        if credentials is None:
            credentials = service_account.Credentials.from_service_account_file(service_account_secret, scopes = scopes)
        self._session = AuthorizedSession(credentials = credentials)

    #################################################
    # Utilities
    #################################################
    def _seqr_agent_header(sefl, headers=None):
        """ Return request headers for Terra API message.
            Inserts seqr/version as the User-Agent.
        Args:
            headers (dict): Include additional headers as key-value pairs
        """
        seqr_headers = {"User-Agent": SEQR_USER_AGENT}
        if headers is not None:
            seqr_headers.update(headers)
        return seqr_headers

    def __get(self, methcall, headers=None, root_url=None, **kwargs):
        """ Call Terra API with HTTP GET method with an authentication header.
        Args:
            methcall: A string of API path (start right after the domain name without leading slash (/)
            headers (dict): Include additional headers as key-value pairs
            root_url: the url up to the domain name ending with a slash (/)
            kwargs: other parameters for the HTTP call, e.g. queries.
        Return:
            HTTP response
        """
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        return self._session.get(urljoin(root_url, methcall), headers = headers, **kwargs)

    def __post(self, methcall, headers=None, root_url=None, **kwargs):
        """ See the __get() method
        """
        if not headers:
            headers = self._seqr_agent_header({"Content-type": "application/json"})
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        return self._session.post(urljoin(root_url, methcall), headers = headers, **kwargs)

    def __put(self, methcall, headers=None, root_url=None, **kwargs):
        """ See the __get() method
        """
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        return self._session.put(urljoin(root_url, methcall), headers = headers, **kwargs)

    def __delete(self, methcall, headers=None, root_url=None):
        """ See the __get() method
        """
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        return self._session.delete(urljoin(root_url, methcall), headers = headers)

    def get_billing_projects(self):
        """Get activation information for the logged-in user.
        :returns a list of billing project dictionary
        """
        r = self.__get("api/profile/billing")
        if r.status_code is not 200:
            raise TerraAPIException(
                'Error: called Terra API "api/profile/billing" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def get_anvil_profile(self):
        """Get activation information for the logged-in user.
        """
        r = self.__get("register")
        if r.status_code is not 200:
            raise TerraAPIException(
                'Error: called Terra API "register" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def list_workspaces(self, fields=None):
        """Get all the workspaces accessible by the logged-in user.

        Args:
        fields (str): a comma-delimited list of values that limits the
            response payload to include only those keys and exclude other
            keys (e.g., to include {"workspace": {"attributes": {...}}},
            specify "workspace.attributes").
        """
        if fields is None:
            r = self.__get("api/workspaces")
        else:
            r = self.__get("api/workspaces", params = {"fields": fields})
        if r.status_code is not 200:
            raise TerraAPIException(
                'Error: called Terra API "api/workspaces" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        return json.loads(r.text)

    def get_workspace_acl(self, namespace, workspace):
        """Request FireCloud access control list for workspace.
        Args:
            namespace (str): project to which workspace belongs
            workspace (str): Workspace name
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
        uri = "api/workspaces/{0}/{1}/acl".format(namespace, workspace)
        r = self.__get(uri)
        if r.status_code is not 200:
            raise TerraAPIException(
                'Error: called Terra API "{}" got status: {} with a reason: {}'.format(uri, r.status_code, r.reason))
        return json.loads(r.text)['acl']

    def get_staffs(self):
        """Request members of seqr staff group.
        """
        r = self.__get("api/groups/seqr-staffs")
        if r.status_code is not 200:
            raise TerraAPIException(
                'Error: called Terra API "api/groups/seqr-staffs" got status: {} with a reason: {}'.format(r.status_code, r.reason))
        group = json.loads(r.text)
        return group["adminsEmails"]

service_account_session = AnvilSession(scopes = scopes)
