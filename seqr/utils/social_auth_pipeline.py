import logging

from django.shortcuts import redirect
from google.oauth2.credentials import Credentials

from seqr.views.utils.terra_api_utils import AnvilSession, TerraAPIException

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        credentials = Credentials(token = response['access_token'])
        session = AnvilSession(credentials = credentials)
        try:
            _ = session.get("register")
        except TerraAPIException as et:  # The user hasn't registered on AnVIL, authentication failed
            logger.info('User {} is trying to login without registration on AnVIL. {}'.format(response['email'], str(et)))
            return redirect('/login?googleLoginFailed=true')
