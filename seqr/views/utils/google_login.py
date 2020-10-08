
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login

import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials

import logging

from settings import GOOGLE_AUTH_CLIENT_CONFIG
from seqr.models import AnvilUser
from seqr.views.utils.terra_api_utils import AnvilSession, scopes, anvilSessionStore

logger = logging.getLogger(__name__)


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


def google_login_view(request):
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
  request.session['google_auth'] = {
      'state': state,
      'origin': request.GET['origin'] if request.GET.get('origin') else '/' ,
      'connect_anvil': request.GET.get('connect_anvil'),
  }

  try:
      return HttpResponseRedirect(authorization_url)
  except Exception as e:
      return HttpResponse('Redirecting to the authorization url failed ({}).'.format(str(e)))


def google_grant_view(request):
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = request.session['google_auth']['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        GOOGLE_AUTH_CLIENT_CONFIG, scopes = scopes, state = state)
    flow.redirect_uri = GOOGLE_AUTH_CLIENT_CONFIG['web']['redirect_uris'][0]

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.get_raw_uri()
    flow.fetch_token(authorization_response = authorization_response)

    token = flow.credentials.id_token

    try:
        # Decode the id token (It is a JWT token actually) to get user ID info
        idinfo = id_token.verify_oauth2_token(token, requests.Request())
    except ValueError as ve:
        logger.warning('Login attempt failed for verify OAuth2 token exception.')
        return HttpResponse('<p>message: {}</p><a href={}>Return</a>'.format(str(ve), request.session['google_auth']['origin']))

    credentials = Credentials(**credentials_to_dict(flow.credentials))
    session = AnvilSession(credentials = credentials, scopes = scopes)
    try:
        # Todo: use the anvil profile for the user name instead of using the name from the User model
        _ = session.get_anvil_profile()
    except Exception as ee:
        logger.warning('User {} attempted logging in without registering with AnVIL. {}'.format(idinfo['email'], str(ee)))
        return HttpResponse('<p>Google account {} has\'t been registered on AnVIL yet.</p>'
            '<p>Please open <a href=https://anvil.terra.bio>https://anvil.terra.bio</a> to sign in with Google and register the account.</p>'
            '<a href={}>Return</a>'.format(idinfo['email'], request.session['google_auth']['origin']))

    # Use user's Google ID to look for the user record in the model
    anvil_user = AnvilUser.objects.filter(email__iexact = idinfo['email']).first()

    if request.session.get('connect_anvil_origin'):  # Local logged in user is registering an AnVIL account
        if anvil_user:  # AnVIL account is occupied
            return HttpResponse('<p>AnVIL account {} has been used by other seqr account</p><a href={}>Return</a>'.format(idinfo['email'], request.session['google_auth']['origin']))
        AnvilUser(user = request.user, email = idinfo['email']).save()
        return HttpResponseRedirect(request.session['google_auth']['origin'])

    if anvil_user:  # The user has registered on seqr
        user = anvil_user.user
    else:  # Un-registered user, auto-register the Google account to the local account with the same email address
        user, created = User.objects.get_or_create(email__iexact = idinfo['email'])
        if created:
            user.username = User.objects.make_random_password()
            user.save()
        anvil_user = AnvilUser(user = user, email = idinfo['email']).save()

    # A temporary solution for Django authenticating the user without a password
    # user.backend = 'django.contrib.auth.backends.ModelBackend'
    request.session['anvil'] = True
    login(request, user, backend = 'django.contrib.auth.backends.ModelBackend')
    anvilSessionStore.update_session(user, session)

    logger.info('AnVIL User {} logged in.'.format(idinfo['email']))
    return HttpResponseRedirect(request.session['google_auth']['origin'])
