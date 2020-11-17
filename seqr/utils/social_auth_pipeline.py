import logging

from django.shortcuts import redirect

from seqr.views.utils.terra_api_utils import anvil_call, TerraNoAccessException

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        try:
            anvil_call('get', 'register', response['access_token'])
        except TerraNoAccessException as et:
            logger.warning('User {} is trying to login without registration on AnVIL. {}'.format(response['email'], str(et)))
            return redirect('/login?googleLoginFailed=true')


def log_signed_in(backend, response, *args, **kwargs):
    logger.info('Logged in {}(AnVIL)'.format(response['email']))
