"""
Utility functions related to authentication.
"""
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

import json
import logging

from seqr.views.utils.json_utils import create_json_response


logger = logging.getLogger(__name__)

API_LOGIN_REQUIRED_URL = '/api/login-required-error'


@csrf_exempt
def login_view(request):
    request_json = json.loads(request.body)
    if not request_json.get('email'):
        return create_json_response({}, status=400, reason='Email is required')
    if not request_json.get('password'):
        return create_json_response({}, status=400, reason='Password is required')

    users = User.objects.filter(email__iexact=request_json['email'])
    if users.count() != 1:
        return create_json_response({}, status=401, reason='Invalid credentials')

    u = authenticate(username=users.first().username, password=request_json['password'])
    if not u:
        return create_json_response({}, status=401, reason='Invalid credentials')

    login(request, u)

    return create_json_response({'success': True})


def logout_view(request):
    logout(request)
    return redirect('/login')


def login_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the login page.
    """
    assert not request.user.is_authenticated()

    return create_json_response({}, status=401, reason="login required")
