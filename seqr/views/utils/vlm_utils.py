import requests

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from settings import VLM_CLIENT_ID, VLM_CLIENT_SECRET, VLM_AUTH_API

logger = SeqrLogger(__name__)

VLM_CREDENTIALS_BODY = {
    'client_id': VLM_CLIENT_ID,
    'client_secret': VLM_CLIENT_SECRET,
    'audience': f'{VLM_AUTH_API}api/v2/',
    'grant_type': 'client_credentials',
}

TOKEN_CACHE_KEY = 'VLM_TOKEN' # nosec
CLIENTS_CACHE_KEY = 'VLM_CLIENTS'

def vlm_lookup(user, chrom, pos, ref, alt, genome_version=None, **kwargs):
    token = _get_cached_auth0_response(
        TOKEN_CACHE_KEY, path='oauth/token', method='POST', data=VLM_CREDENTIALS_BODY,
        parse_response=lambda response_json: response_json.get('access_token'),
    )

    headers = {'Authorization': f'Bearer {token}'}
    clients = _get_cached_auth0_response(CLIENTS_CACHE_KEY, path='api/v2/clients', headers=headers, params={
        'fields': 'client_id,name,client_metadata', 'is_global': 'false',
    }, parse_response=_parse_clients_response)

    genome_version = GENOME_VERSION_LOOKUP[genome_version or GENOME_VERSION_GRCh38]
    params = {
        'assemblyId': genome_version, 'referenceName': chrom, 'start': pos, 'referenceBases': ref, 'alternateBases': alt,
    }

    results = {}
    for client_name, match_url in clients.items():
        logger.info(f'VLM match request to {client_name}', user, detail=params)
        try:
            response = requests.get(match_url, headers=headers, params=params, timeout=120)
            response.raise_for_status()
            response_json = response.json()
            results[client_name] = {
                meta['handoverType']['id']: {'url': meta['url'], 'counts': {}}
                for meta in response_json['beaconHandovers']
            }
            for result in response_json['response']['resultSets']:
                parsed_id = result['id'].rsplit(' ', 1)
                count_type = parsed_id[-1]
                result_id =  parsed_id[0] if len(parsed_id) == 2 else next(iter(results[client_name].keys()))
                results[client_name][result_id]['counts'][count_type] = result['resultsCount']
        except Exception as e:
            logger.error(f'VLM match error for {client_name}: {e}', user, detail=params)

    return results


def _get_cached_auth0_response(cache_key, path, parse_response, method='GET', **kwargs):
    value = safe_redis_get_json(cache_key)
    if value and cache_key:
        return value

    response = requests.request(method, f'{VLM_AUTH_API}{path}', **kwargs)
    response.raise_for_status()
    value = parse_response(response.json())

    safe_redis_set_json(cache_key, value, expire=60*60*24)  # Cache for 24 hours
    return value

def _parse_clients_response(clients):
    return {
        client['name']: client['client_metadata']['match_url'] for client in clients
        if client['client_id'] != VLM_CLIENT_ID and client.get('client_metadata', {}).get('match_url')
    }
