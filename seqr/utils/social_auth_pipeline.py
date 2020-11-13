import logging

from django.shortcuts import redirect

from seqr.views.utils.terra_api_utils import anvil_call, TerraAPIException

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        try:
            anvil_call('get', 'register', access_token=response['access_token'])
        except TerraAPIException as et:
            logger.info('User {} is trying to login without registration on AnVIL. {}'.format(response['email'], str(et)))
            return redirect('/login?googleLoginFailed=true')
