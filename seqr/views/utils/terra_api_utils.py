"""Provide python bindings for the AnVIL Terra API."""

import json
import logging
import time
import requests

from urllib.parse import urljoin

from django.core.exceptions import PermissionDenied
from social_django.utils import load_strategy
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json

from settings import SEQR_VERSION, TERRA_API_ROOT_URL, TERRA_PERMS_CACHE_EXPIRE_SECONDS, \
    TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS, SOCIAL_AUTH_GOOGLE_OAUTH2_KEY, SERVICE_ACCOUNT_FOR_ANVIL, SOCIAL_AUTH_PROVIDER

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION
OWNER_ACCESS_LEVEL = 'OWNER'
WRITER_ACCESS_LEVEL = 'WRITER'
READER_ACCESS_LEVEL = 'READER'
PROJECT_OWNER_ACCESS_LEVEL = 'PROJECT_OWNER'
CAN_SHARE_PERM = 'canShare'

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


class TerraRefreshTokenFailedException(TerraAPIException):
    def __init__(self, message):
        """
        Custom Exception to capture refresh token failures. Maps to 401 error to redirect user to login

        :param message: error message
        """
        super(TerraRefreshTokenFailedException, self).__init__(message, 401)


def google_auth_enabled():
    return bool(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY)


def anvil_enabled():
    return bool(TERRA_API_ROOT_URL)


def is_google_authenticated(user):
    return bool(_safe_get_social(user))


def remove_token(user):
    social = _safe_get_social(user)
    if social and social.extra_data:
        social.extra_data.pop('access_token', None)
        social.extra_data['expires'] = 0
        social.save()


def is_anvil_authenticated(user):
    if not anvil_enabled():
        return False

    social = _safe_get_social(user)
    if social and social.extra_data:
        return social.extra_data.get('access_token', '') != ''

    return False


def _get_call_args(path, headers=None, root_url=None):
    if headers is None:
        headers = {"User-Agent": SEQR_USER_AGENT}
    headers.update({"accept": "application/json", "Content-Type": "application/json"})
    if root_url is None:
        root_url = TERRA_API_ROOT_URL
    url = urljoin(root_url, path)
    return url, headers


def _safe_get_social(user):
    if not google_auth_enabled() or not hasattr(user, 'social_auth'):
        return None

    social = user.social_auth.filter(provider=SOCIAL_AUTH_PROVIDER)
    return social.first() if social else None


def _get_social_access_token(user):
    social = _safe_get_social(user)
    if (social.extra_data['auth_time'] + social.extra_data['expires'] - 10) <= int(
            time.time()):  # token expired or expiring?
        strategy = load_strategy()
        logger.info('Refreshing access token', extra={'user': user})
        try:
            social.refresh_token(strategy)
        except Exception as ee:
            logger.warning('Refresh token failed. {}'.format(str(ee)), extra={'user': user})
            raise TerraRefreshTokenFailedException('Refresh token failed. {}'.format(str(ee)))
    return social.extra_data['access_token']


def anvil_call(method, path, access_token, user=None, headers=None, root_url=None, data=None, handle_errors=False):
    url, headers = _get_call_args(path, headers, root_url)
    request_func = getattr(requests, method)
    headers.update({'Authorization': 'Bearer {}'.format(access_token)})
    r = request_func(url, data=data, headers=headers)

    exception = None
    if r.status_code == 404:
        exception = TerraNotFoundException('{} called Terra API: {} /{} got status 404 with reason: {}'
                                     .format(user, method.upper(), path, r.reason))
    elif r.status_code == 403:
        exception = PermissionDenied('{} got access denied (403) from Terra API: {} /{} with reason: {}'
                               .format(user, method.upper(), path, r.reason))

    elif r.status_code != 200:
        exception  = TerraAPIException('Error: called Terra API: {} /{} got status: {} with a reason: {}'.format(method.upper(),
            path, r.status_code, r.reason), r.status_code)

    if exception:
        if handle_errors:
            logger.warning(str(exception))
            return {}
        raise exception  # pylint: disable=raising-bad-type

    logger.info('{} {} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text), user))

    return json.loads(r.text)


def _user_anvil_call(method, path, user, data=None, handle_errors=False):
    access_token = _get_social_access_token(user)
    return anvil_call(method, path, access_token, user=user, data=data, handle_errors=handle_errors)


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


def user_get_workspace_access_level(user, workspace_namespace, workspace_name, meta_fields=None):
    fields = ',{}'.format(','.join(meta_fields)) if meta_fields else ''
    path = "api/workspaces/{0}/{1}?fields=accessLevel,canShare{2}".format(workspace_namespace, workspace_name, fields)

    cache_key = 'terra_req__{}__{}'.format(user, path)
    r = safe_redis_get_json(cache_key)
    if r:
        logger.info('Terra API cache hit for: GET {} {}'.format(path, user))
        return r

    # Exceptions are handled to return an empty result for users who have no permission to access the workspace
    r = _user_anvil_call('get', path, user, handle_errors=True)

    if r:
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
    # Exceptions are handled to return an empty result for the users who have no permission to access the acl
    return _user_anvil_call('get', path, user, handle_errors=True).get('acl', {})


def add_service_account(user, workspace_namespace, workspace_name):
    """
    Add the seqr service account to the workspace on AnVIL.

    The user must have the "can share" privilege for the workspace.

    :param user: the seqr user object
    :param workspace_namespace: namespace or billing project name of the workspace
    :param workspace_name: name of the workspace on AnVIL. The name will also be used as the name of project in seqr
    :return: True if service account was added, False if it was already associated with the workspace
    """
    if has_service_account_access(user, workspace_namespace, workspace_name):
        return False
    acl = [
             {
               "email": SERVICE_ACCOUNT_FOR_ANVIL,
               "accessLevel": "READER",
               "canShare": False,
               "canCompute": False
             }
          ]
    path = "api/workspaces/{0}/{1}/acl".format(workspace_namespace, workspace_name)
    r = _user_anvil_call('patch', path, user, data=json.dumps(acl))
    if not (r['usersUpdated'] and r['usersUpdated'][0]['email'] == SERVICE_ACCOUNT_FOR_ANVIL):
        message = 'Failed to grant seqr service account access to the workspace {}/{}'.format(workspace_namespace, workspace_name)
        raise TerraAPIException(message, 400)
    return True


def has_service_account_access(user, workspace_namespace, workspace_name):
    acl = user_get_workspace_acl(user, workspace_namespace, workspace_name)
    service_account = acl.get(SERVICE_ACCOUNT_FOR_ANVIL)
    return bool(service_account and (not service_account['pending']))
