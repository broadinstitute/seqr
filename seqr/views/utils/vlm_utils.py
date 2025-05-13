import requests

from reference_data.models import GENOME_VERSION_GRCh38
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from settings import VLM_CLIENT_ID, VLM_CLIENT_SECRET, VLM_AUTH_API

TOKEN_CACHE_KEY = 'VLM_TOKEN'
CLIENTS_CACHE_KEY = 'VLM_CLIENTS'

def vlm_lookup(user, chrom, pos, ref, alt, genome_version=None, **kwargs):
    token = _get_cached_value(TOKEN_CACHE_KEY, _get_vlm_token)
    headers = {'Authorization': f'Bearer {token}'}
    clients = _get_cached_value(CLIENTS_CACHE_KEY, _get_vlm_clients, headers=headers)

    genome_version = genome_version or GENOME_VERSION_GRCh38
    return clients


def _get_cached_value(cache_key, fetch_func, **kwargs):
    value = safe_redis_get_json(cache_key)
    if value:
        return value

    value = fetch_func(**kwargs)
    safe_redis_set_json(cache_key, value, expire=60*60*24)  # Cache for 24 hours
    return value


def _get_vlm_token():
    response = requests.post(
        f'{VLM_AUTH_API}/oauth/token',
        data={
            'client_id': VLM_CLIENT_ID,
            'client_secret': VLM_CLIENT_SECRET,
            'audience': f'{VLM_AUTH_API}api/v2/',
            'grant_type': 'client_credentials',
        },
    )
    response.raise_for_status()
    return response.json().get('access_token')


def _get_vlm_clients(headers=None):
    response = requests.get(f'{VLM_AUTH_API}/api/v2/clients', headers=headers, params={
        'fields': 'client_id,name,client_metadata', 'is_global': 'false',
    })
    response.raise_for_status()
    return response.json()