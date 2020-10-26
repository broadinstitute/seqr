import logging
import requests

from django.shortcuts import redirect

from seqr.views.utils.terra_api_utils import _get_call_args

logger = logging.getLogger(__name__)


def validate_anvil_registration(backend, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        url, headers = _get_call_args('register')
        headers.update({'Authorization': 'Bearer {}'.format(response['access_token'])})
        r = requests.get(url, headers=headers)
        if r.status_code != 200:  # The user hasn't registered on AnVIL, authentication failed
            logger.info('User {} is trying to login without registration on AnVIL.'.format(response['email']))
            return redirect('/login?googleLoginFailed=true')
