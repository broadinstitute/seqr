"""
Utility functions related to authentication.
"""
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.db.models.functions import Lower
from django.shortcuts import redirect

import json
import logging

from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import user_is_data_manager
from settings import SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

logger = logging.getLogger(__name__)


def login_view(request):
    request_json = json.loads(request.body)
    if not request_json.get('email'):
        return create_json_response({}, status=400, reason='Email is required')
    if not request_json.get('password'):
        return create_json_response({}, status=400, reason='Password is required')

    # Django's iexact filtering will improperly match unicode characters, which creates a security risk.
    # Instead, query for the lower case match to allow case-insensitive matching
    users = User.objects.annotate(email_lower=Lower('email')).filter(email_lower=request_json['email'].lower())
    if users.count() != 1:
        return create_json_response({}, status=401, reason='Invalid credentials')

    user = users.first()
    if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY and (user_is_data_manager(user) or user.is_superuser):
        logger.warning("Privileged user {} is trying to login without Google authentication.".format(user))
        return create_json_response({}, status=401, reason='Privileged user must login with Google authentication.')

    u = authenticate(username=user.username, password=request_json['password'])
    if not u:
        return create_json_response({}, status=401, reason='Invalid credentials')

    login(request, u)
    logger.info('Logged in {}'.format(u.email), extra={'user': u})

    return create_json_response({'success': True})


def logout_view(request):
    user = request.user
    logout(request)
    logger.info('Logged out {}'.format(user.email), extra={'user': user})
    return redirect('/login')


def login_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the login page.
    """
    return create_json_response({}, status=401, reason="login required")
