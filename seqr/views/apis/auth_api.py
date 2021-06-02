"""
Utility functions related to authentication.
"""
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models.functions import Lower
from django.shortcuts import redirect

import json
import logging

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import user_is_data_manager
from seqr.views.utils.terra_api_utils import google_auth_enabled, remove_token

logger = logging.getLogger(__name__)


def login_view(request):
    if google_auth_enabled():
        error = 'Password-based authentication is disabled. Please use Google authentication instead.'
        return create_json_response({'error': error}, status=401, reason=error)

    request_json = json.loads(request.body)
    if not request_json.get('email'):
        error = 'Email is required'
        return create_json_response({'error': error}, status=400, reason=error)
    if not request_json.get('password'):
        error = 'Password is required'
        return create_json_response({'error': error}, status=400, reason=error)

    # Django's iexact filtering will improperly match unicode characters, which creates a security risk.
    # Instead, query for the lower case match to allow case-insensitive matching
    users = User.objects.annotate(email_lower=Lower('email')).filter(email_lower=request_json['email'].lower())
    if users.count() != 1:
        error = 'Invalid credentials'
        return create_json_response({'error': error}, status=401, reason=error)

    user = users.first()
    if google_auth_enabled() and (user_is_data_manager(user) or user.is_superuser):
        logger.warning("Privileged user {} is trying to login without Google authentication.".format(user))
        error = 'Privileged user must login with Google authentication.'
        return create_json_response({'error': error}, status=401, reason=error)

    u = authenticate(username=user.username, password=request_json['password'])
    if not u:
        error = 'Invalid credentials'
        return create_json_response({'error': error}, status=401, reason=error)

    login(request, u)
    logger.info('Logged in {}'.format(u.email), extra={'user': u})

    return create_json_response({'success': True})


@login_required(redirect_field_name=None)
def logout_view(request):
    user = request.user
    remove_token(user)
    logout(request)
    logger.info('Logged out {}'.format(user.email), extra={'user': user})
    return redirect('/login')


def login_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the login page.
    """
    return _unauthorized_error('login')


def policies_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the accept policies page.
    """
    return _unauthorized_error('policies')


def _unauthorized_error(error):
    return create_json_response({'error': error} , status=401, reason="{} required".format(error))
