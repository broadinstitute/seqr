
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import login, authenticate

import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials

import logging

from settings import GOOGLE_AUTH_CLIENT_CONFIG
from seqr.views.utils.terra_api_utils import scopes, anvilSessionStore

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

    credentials = Credentials(**credentials_to_dict(flow.credentials))
    user = authenticate(token = flow.credentials.id_token, creds = credentials)

    if not user or not hasattr(user, 'anviluser'):
        logger.warning("Failed to login a user with Google".format(authorization_response))
        return HttpResponse('<p>Login failed.</p><p>Make sure you have registered your account on '
            '<a href=https://anvil.terra.bio>https://anvil.terra.bio</a> to sign in with Google and register the account.</p>'
            '<a href={}>Return</a>'.format(request.session['google_auth']['origin']))

    # Local logged in user is registering an AnVIL account
    if request.session.get('connect_anvil_origin'):
        if user != request.user:  # AnVIL account is occupied
            return HttpResponse('<p>AnVIL account {} has been used by other seqr account</p><a href={}>Return</a>'
                                .format(request.user.useranvil_user.email, request.session['google_auth']['origin']))
        return HttpResponseRedirect(request.session['google_auth']['origin'])

    # Login user
    login(request, user)
    request.session['anvil'] = True
    anvilSessionStore.add_session(user, credentials, request.session.session_key)

    logger.info('AnVIL User {} logged in.'.format(user.anviluser.email))
    return HttpResponseRedirect(request.session['google_auth']['origin'])
