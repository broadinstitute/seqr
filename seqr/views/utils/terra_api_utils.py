# This module provides python bindings for the AnVIL Terra API.

import json
import logging
import time
import requests
import hashlib

from urllib.parse import urljoin

from django.core.exceptions import PermissionDenied
from social_django.models import UserSocialAuth
from social_django.utils import load_strategy
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json

from settings import SEQR_VERSION, TERRA_API_ROOT_URL, TERRA_API_CACHE_EXPIRE_SECONDS

SEQR_USER_AGENT = "seqr/" + SEQR_VERSION

logger = logging.getLogger(__name__)


class TerraAPIException(Exception):
    pass


class TerraNotFoundException(TerraAPIException):
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


def _get_social_access_token(user):
    social = user.social_auth.get(provider = 'google-oauth2')
    if (social.extra_data['auth_time'] + social.extra_data['expires'] - 10) <= int(
            time.time()):  # token expired or expiring?
        strategy = load_strategy()
        try:
            social.refresh_token(strategy)
        except Exception as ee:
            logger.warning('Refresh token failed. {}'.format(str(ee)))
            raise TerraAPIException('Refresh token failed. {}'.format(str(ee)))
    return social.extra_data['access_token']


def anvil_call(method, path, access_token, user=None, headers=None, root_url=None, **kwargs):
    url, headers = _get_call_args(path, headers, root_url)
    request_func = getattr(requests, method)
    headers.update({'Authorization': 'Bearer {}'.format(access_token)})
    cache_key = 'terra_req__' + hashlib.md5((url + str(headers) + str(kwargs)).encode('utf-8')).hexdigest()
    r_text = safe_redis_get_json(cache_key)
    if r_text:
        logger.info('Debug: Cache {} hit. {}'.format(cache_key, r_text))
        return json.loads(r_text)

    r = request_func(url, headers=headers, **kwargs)

    if r.status_code == 404:
        raise TerraNotFoundException('{} called Terra API: {} /{} got status 404 with reason: {}'
                                     .format(user, method.upper(), path, r.reason))
    if r.status_code == 403:
        raise PermissionDenied('{} got access denied (403) from Terra API: {} /{} with reason: {}'
                               .format(user, method.upper(), path, r.reason))

    if r.status_code != 200:
        logger.error('{} {} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text), user))
        raise TerraAPIException('Error: called Terra API: {} /{} got status: {} with a reason: {}'.format(method.upper(),
            path, r.status_code, r.reason))

    logger.info('{} {} {} {} {}'.format(method.upper(), url, r.status_code, len(r.text), user))

    safe_redis_set_json(cache_key, r.text, TERRA_API_CACHE_EXPIRE_SECONDS)

    return json.loads(r.text)


def _user_anvil_call(method, path, user, **kwargs):
    access_token = _get_social_access_token(user)
    return anvil_call(method, path, access_token, user=user, **kwargs)


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


def user_get_workspace_access_level(user, workspace_namespace, workspace_name):
    path = "api/workspaces/{0}/{1}?fields=accessLevel".format(workspace_namespace, workspace_name)
    try:
        return _user_anvil_call('get', path, user)
    except TerraNotFoundException as et:
        logger.warning(str(et))
        return {}


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
    except (TerraNotFoundException, PermissionDenied) as et:
        logger.warning(str(et))
        return {}
