import logging

from django.shortcuts import redirect
from google.oauth2.credentials import Credentials

from seqr.views.utils.terra_api_utils import AnvilSession

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        credentials = Credentials(token = response['access_token'])
        session = AnvilSession(credentials = credentials)
        r = session.get("register")
        if r.status_code != 200: # The user hasn't registered on AnVIL, authentication failed
            logger.info('User {} is trying to login without registration on AnVIL.'.format(response['email']))
            return redirect('/login?googleLoginFailed=true')
