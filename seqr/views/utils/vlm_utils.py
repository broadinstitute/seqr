import requests

from reference_data.models import GENOME_VERSION_GRCh38
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from settings import VLM_CLIENT_ID, VLM_CLIENT_SECRET, VLM_AUTH_API

VLM_CREDENTIALS_BODY = {
    'client_id': VLM_CLIENT_ID,
    'client_secret': VLM_CLIENT_SECRET,
    'audience': f'{VLM_AUTH_API}api/v2/',
    'grant_type': 'client_credentials',
}

TOKEN_CACHE_KEY = 'VLM_TOKEN'
CLIENTS_CACHE_KEY = 'VLM_CLIENTS'

def vlm_lookup(user, chrom, pos, ref, alt, genome_version=None, **kwargs):
    token = _get_cached_vlm_response(
        TOKEN_CACHE_KEY, 'oauth/token', 'POST', data=VLM_CREDENTIALS_BODY, response_key='access_token',
    )

    headers = {'Authorization': f'Bearer {token}'}
    clients = _get_cached_vlm_response(CLIENTS_CACHE_KEY, 'api/v2/clients', headers=headers, params={
        'fields': 'client_id,name,client_metadata', 'is_global': 'false',
    })

    genome_version = genome_version or GENOME_VERSION_GRCh38
    return clients


def _get_cached_vlm_response(cache_key, path, method='GET', response_key=None, **kwargs):
    value = safe_redis_get_json(cache_key)
    if value:
        return value

    response = requests.request(method, f'{VLM_AUTH_API}/{path}', **kwargs)
    response.raise_for_status()
    value = response.json()
    if response_key:
        value = value.get(response_key)

    safe_redis_set_json(cache_key, value, expire=60*60*24)  # Cache for 24 hours
    return value
