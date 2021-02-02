# This module provides python bindings for the AnVIL Terra API.

import json
import logging
import time
import requests

from urllib.parse import urljoin

from django.core.exceptions import PermissionDenied
from social_django.models import UserSocialAuth
from social_django.utils import load_strategy
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json

from settings import SEQR_VERSION, TERRA_API_ROOT_URL, TERRA_PERMS_CACHE_EXPIRE_SECONDS, \
    TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS, SOCIAL_AUTH_GOOGLE_OAUTH2_KEY, SERVICE_ACCOUNT_FOR_ANVIL

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

logger = logging.getLogger(__name__)


class TerraAPIException(Exception):
    def __init__(self, message, status_code):
        """
        Custom Exception to capture Terra API call failures

        :param message: error message
        :param status_code: the status code associated with the failed request
        """
        super(TerraAPIException, self).__init__(message)
        self.status_code = status_code


class TerraNotFoundException(TerraAPIException):
    def __init__(self, message):
        """
        Custom Exception to capture Terra API calls that fail with 404 Not Found

        :param message: error message
        """
        super(TerraNotFoundException, self).__init__(message, 404)


def google_auth_enabled():
    return bool(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY)


def anvil_enabled():
    return bool(TERRA_API_ROOT_URL)


def is_google_authenticated(user):
    if not google_auth_enabled():
        return False
    try:
        _ = user.social_auth.get(provider = 'google-oauth2')
    except UserSocialAuth.DoesNotExist:  # Exception happen when the user has never logged-in with Google
        return False
    return True


def is_anvil_authenticated(user):
    return anvil_enabled() and is_google_authenticated(user)


def _get_call_args(path, headers=None, root_url=None):
    if headers is None:
        headers = {"User-Agent": SEQR_USER_AGENT}
    headers.update({"accept": "application/json"})
    if root_url is None:
        root_url = TERRA_API_ROOT_URL
    url = urljoin(root_url, path)
    return url, headers


def _get_social_access_token(user):
    social = user.social_auth.get(provider = 'google-oauth2')
    if (social.extra_data['auth_time'] + social.extra_data['expires'] - 10) <= int(
            time.time()):  # token expired or expiring?
        strategy = load_strategy()
        try:
            social.refresh_token(strategy)
        except Exception as ee:
            logger.warning('Refresh token failed. {}'.format(str(ee)))
            raise TerraAPIException('Refresh token failed. {}'.format(str(ee)), 401)
    return social.extra_data['access_token']


def anvil_call(method, path, access_token, user=None, headers=None, root_url=None, data=None):
    url, headers = _get_call_args(path, headers, root_url)
    request_func = getattr(requests, method)
    headers.update({'Authorization': 'Bearer {}'.format(access_token)})
    r = request_func(url, headers=headers, data=data)

    if r.status_code == 404:
        raise TerraNotFoundException('{} called Terra API: {} /{} got status 404 with reason: {}'
                                     .format(user, method.upper(), path, r.reason))
    if r.status_code == 403:
        raise PermissionDenied('{} got access denied (403) from Terra API: {} /{} with reason: {}'
                               .format(user, method.upper(), path, r.reason))

    if r.status_code != 200:
        logger.error('{} {} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text), user))
        raise TerraAPIException('Error: called Terra API: {} /{} got status: {} with a reason: {}'.format(method.upper(),
            path, r.status_code, r.reason), r.status_code)

    logger.info('{} {} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text), user))

    return json.loads(r.text)


def _user_anvil_call(method, path, user, data=None):
    access_token = _get_social_access_token(user)
    return anvil_call(method, path, access_token, user=user, data=data)


def list_anvil_workspaces(user):
    """Get all the workspaces accessible by the logged-in user.

    :param
    user (User model): who's credentials will be used to access AnVIL
    :return
    A list of workspaces that the user has access (OWNER, WRITER, or READER). Each of the workspace has
    its name and namespace.

    """
    path = 'api/workspaces?fields=public,workspace.name,workspace.namespace'
    cache_key = 'terra_req__{}__{}'.format(user, path)
    r = safe_redis_get_json(cache_key)
    if r:
        logger.info('Terra API cache hit for: GET {} {}'.format(path, user))
        return r

    r = _user_anvil_call('get', path, user)

    # remove the public workspaces which can't be the projects in seqr
    r = [{'workspace': ws['workspace']} for ws in r if not ws.get('public', True)]

    safe_redis_set_json(cache_key, r, TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS)

    return r


def user_get_workspace_access_level(user, workspace_namespace, workspace_name):
    path = "api/workspaces/{0}/{1}?fields=accessLevel".format(workspace_namespace, workspace_name)

    cache_key = 'terra_req__{}__{}'.format(user, path)
    r = safe_redis_get_json(cache_key)
    if r:
        logger.info('Terra API cache hit for: GET {} {}'.format(path, user))
        return r

    try:
        r = _user_anvil_call('get', path, user)
    # TerraNotFoundException is handled to allow seqr continue working when Terra is not available
    except TerraNotFoundException as et:
        logger.warning(str(et))
        return {}

    safe_redis_set_json(cache_key, r, TERRA_PERMS_CACHE_EXPIRE_SECONDS)

    return r


def user_get_workspace_acl(user, workspace_namespace, workspace_name):
    """
    Requests AnVIL access control list for a workspace with a service account (sa).

    The workspace of AnVIL is identified by its namespace and name.

    Args:
        user (User object): the user who makes the request
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

    """
    path = "api/workspaces/{0}/{1}/acl".format(workspace_namespace, workspace_name)
    try:
        return _user_anvil_call('get', path, user).get('acl', {})
    # Exceptions are handled to avoid error when a non-anvil user trying to validate permissions on AnVIL
    except (TerraNotFoundException, PermissionDenied) as et:
        logger.warning(str(et))
        return {}


def update_workspace_acl(user, workspace_namespace, workspace_name, acl):
    """
    Update workspace acl.

    The user must have the "can share" privilege for the workspace.

    :param user: the seqr user object
    :param workspace_namespace: namespace or billing project name of the workspace
    :param workspace_name: name of the workspace on AnVIL. The name will also be used as the name of project in seqr
    :param acl: the list of acl to be updated
    :return: an object about the operation. See details at https://api.firecloud.org/#/Workspaces/updateWorkspaceACL

    """
    path = "api/workspaces/{0}/{1}/acl".format(workspace_namespace, workspace_name)
    return _user_anvil_call('patch', path, user, data=acl)


def add_service_account(user, workspace_namespace, workspace_name):
    """
    Add the seqr service account to the workspace on AnVIL.

    The user must have the "can share" privilege for the workspace.

    :param user: the seqr user object
    :param workspace_namespace: namespace or billing project name of the workspace
    :param workspace_name: name of the workspace on AnVIL. The name will also be used as the name of project in seqr
    :return: Success: True, Fail: False

    """
    old_acl = user_get_workspace_acl(user, workspace_namespace, workspace_name)
    service_account = old_acl.get(SERVICE_ACCOUNT_FOR_ANVIL)
    if service_account and not service_account['pending']:
        return True
    acl = [
             {
               "email": SERVICE_ACCOUNT_FOR_ANVIL,
               "accessLevel": "READER",
               "canShare": False,
               "canCompute": False
             }
          ]
    users_updated = update_workspace_acl(user, workspace_namespace, workspace_name, acl)['usersUpdated']
    return users_updated and users_updated[0]['email'] == SERVICE_ACCOUNT_FOR_ANVIL
