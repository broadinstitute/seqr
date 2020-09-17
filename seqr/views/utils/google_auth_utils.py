"""
This module provides python bindings for the AnVIL Terra API.
"""

import logging

from urllib.parse import urljoin

import google.auth
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import service_account

from settings import SEQR_VERSION, TERRA_API_CONFIG

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

scopes = ['https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/cloud-billing',
          'openid']

logger = logging.getLogger(__name__)


class AnvilSession:
    def __init__(self, credentials=None, service_account_secret="service_account.json", scopes=None):
        if credentials is None:
            credentials = service_account.Credentials.from_service_account_file(service_account_secret, scopes=scopes)
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
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        r = self._session.get(urljoin(root_url, methcall), headers = headers, **kwargs)
        return r

    def __post(self, methcall, headers=None, root_url=None, **kwargs):
        if not headers:
            headers = self._seqr_agent_header({"Content-type": "application/json"})
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        r = self._session.post(urljoin(root_url, methcall), headers = headers, **kwargs)
        return r

    def __put(self, methcall, headers=None, root_url=None, **kwargs):
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        r = self._session.put(urljoin(root_url, methcall), headers = headers, **kwargs)
        return r

    def __delete(self, methcall, headers=None, root_url=None):
        if not headers:
            headers = self._seqr_agent_header()
        if root_url is None:
            root_url = TERRA_API_CONFIG['root_url']
        r = self._session.delete(urljoin(root_url, methcall), headers = headers)
        return r

    def get_billing_projects(self):
        """Get activation information for the logged-in user.
        Swagger:
            https://api.firecloud.org/#!/profile/billing
        """
        return self.__get("api/profile/billing")

    def get_anvil_profile(self):
        """Get activation information for the logged-in user.
        Swagger:
            https://api.firecloud.org/#!/register
        """
        return self.__get("register")


service_account_session = AnvilSession(scopes = scopes)
