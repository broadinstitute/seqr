"""
Utility functions related to authentication.
"""
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials

import json
import logging

from settings import GOOGLE_AUTH_CLIENT_CONFIG
from seqr.models import AnvilUser
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.terra_api_utils import AnvilSession, scopes

logger = logging.getLogger(__name__)


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

@csrf_exempt
def login_google(request):
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_config(
      GOOGLE_AUTH_CLIENT_CONFIG, scopes=scopes)

  # The URI created here must exactly match one of the authorized redirect URIs
  # for the OAuth 2.0 client, which you configured in the API Console. If this
  # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
  # error.
  flow.redirect_uri = GOOGLE_AUTH_CLIENT_CONFIG['web']['redirect_uris'][0]

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
  request.session['state'] = state

  # Return the url to be sent for the Google Auth server by the the front end
  return create_json_response({'data': authorization_url})

@csrf_exempt
def login_oauth2callback(request):
    """
    Callback function will be called after the OAuth2 server passes the authentication

    In the previous function 'login_google', a redirect url is generated with the information of Google client ID and
    the front end will be redirect to the url to do authentication with Google auth server. Once the authentication has
    passed, the result of the authentication will be sent to the web server through this callback function.
    :param request: includes the authorized code
    :return: status of authorization server and resource server (which is AnVIL server) responses
    """

    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = request.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        GOOGLE_AUTH_CLIENT_CONFIG, scopes = scopes, state = state)
    flow.redirect_uri = GOOGLE_AUTH_CLIENT_CONFIG['web']['redirect_uris'][0]

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.body.decode('utf-8')
    flow.fetch_token(authorization_response = authorization_response)

    token = flow.credentials.id_token

    try:
        # Decode the id token (It is a JWT token actually) to get user ID info
        idinfo = id_token.verify_oauth2_token(token, requests.Request())
    except ValueError as ve:
        return create_json_response({'message': str(ve)}, status=401, reason=str(ve))

    credentials = Credentials(**credentials_to_dict(flow.credentials))
    session = AnvilSession(credentials = credentials, scopes = scopes)
    try:
        # Todo: use the anvil profile for the user name instead of using the name from the User model
        _ = session.get_anvil_profile()
    except Exception as ee:
        return create_json_response({'message': 'Google account {} has\'t been registered on AnVIL yet. '
            'Please open https://anvil.terra.bio to sign in with Google and register the account.'.format(idinfo['email'])},
            status=400, reason='Google account has\'t been registered on AnVIL. Exception: {}'.format(str(ee)))

    # Use user's Google ID to look for the user record in the model
    anvil_user = AnvilUser.objects.filter(email__iexact = idinfo['email']).first()

    if request.user and request.user.id and not request.session.has_key('anvil'):  # Local logged in user is registering an AnVIL account
        if anvil_user: # AnVIL account is occupied
            return create_json_response({}, status = 400,
                reason = 'AnVIL account {} has been used by other seqr account'.format(idinfo['email']))
        AnvilUser(user=request.user, email=idinfo['email']).save()
        return create_json_response({'success': True})

    if anvil_user: # Registered user
        user = anvil_user.user
    else: # Un-registered user, auto-register the Google account to the local account with the same email address
        user = User.objects.filter(email__iexact = idinfo['email']).first()
        if not user:  # User not exist, create one (disabled during transitioning phase)
            create_json_response({}, status = 400, # Todo: remove this statement after transitioning
                reason = "seqr user with email {} doesn't exist".format(idinfo["email"]))
            username = User.objects.make_random_password()
            user = User.objects.create_user(
                username,
                email = 'AnVIL User: {}'.format(idinfo['email']), # AnVIL only user
                first_name = idinfo['email'],
                last_name = '',
                is_staff = False
            )
        AnvilUser(user=user, email=idinfo['email']).save()

    # A temporary solution for Django authenticating the user without a password
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    request.session['anvil'] = session
    login(request, user)

    return create_json_response({'REQUEST_GOOGLE_AUTH_RESULT': {'success': True}})


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


def logout_view(request):
    logout(request)
    return redirect('/login')


def login_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the login page.
    """
    assert not request.user.is_authenticated()

    return create_json_response({}, status=401, reason="login required")
