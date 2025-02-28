import logging

from django.shortcuts import redirect
from urllib.parse import urlencode

from seqr.views.utils.terra_api_utils import anvil_call, TerraNotFoundException

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        try:
            anvil_call('get', 'register', response['access_token'])
        except TerraNotFoundException as et:
            logger.warning('User {} is trying to login without registration on AnVIL. {}'.format(response['email'], str(et)),
                           extra={'user_email': response['email']})
            return _redirect_login_error('anvil_registration', backend)


def validate_user_exist(backend, response, user=None, *args, **kwargs):
    if not user:
        logger.warning('Google user {} is trying to login without an existing seqr account ({}).'
                       .format(response['email'], backend.name), extra={'user_email': response['email']})
        return _redirect_login_error('no_account', backend)


def _redirect_login_error(error, backend):
    params = ''
    next_param = backend.strategy.session_get('next')
    if next_param:
        params = '?{}'.format(urlencode({'next': next_param}))
    return redirect('/login/error/{}{}'.format(error, params))


def log_signed_in(backend, response, is_new=False, *args, **kwargs):
    logger.info('Logged in {} ({})'.format(response['email'], backend.name), extra={'user_email': response['email']})
    if is_new:
        logger.info('Created user {} ({})'.format(response['email'], backend.name), extra={'user_email': response['email']})
