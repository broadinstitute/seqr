from aiohttp import web, ClientSession
import jwt
import logging
import os

logger = logging.getLogger(__name__)

VLM_AUTH_API = 'https://vlm-auth.us.auth0.com/'

VLM_CLIENT_ID = os.environ.get('VLM_CLIENT_ID')
VLM_CLIENT_SECRET = os.environ.get('VLM_CLIENT_SECRET')
VLM_CREDENTIALS = {'client_id': VLM_CLIENT_ID, 'client_secret': VLM_CLIENT_SECRET}

async def authenticate(request: web.Request):
    try:
        scheme, token = request.headers.get('Authorization').strip().split(' ')
    except ValueError:
        raise web.HTTPForbidden(reason='Invalid authorization header')
    if scheme.lower() != 'bearer':
        raise web.HTTPForbidden(reason='Invalid token scheme')
    if not token:
        raise web.HTTPForbidden(reason='Missing authorization token')

    try:
        decoded = jwt.decode(token, algorithms=['RS256'], issuer=VLM_AUTH_API, options={
            'verify_signature': False, 'verify_iss': True, 'verify_exp': True, 'require': ['azp'],
        })
    except jwt.InvalidTokenError as e:
        raise web.HTTPForbidden(reason=f'Invalid token: {e}')

    client_id = decoded['azp']
    client_info = await _get_valid_vlm_client_info(client_id)
    logger.info(f'Received request from {client_info.get("name", client_id)}: {request.query_string}')


async def _get_valid_vlm_client_info(client_id: str) -> dict:
    with ClientSession(VLM_AUTH_API) as session:
        async with session.post('/oauth/token', json=VLM_CREDENTIALS) as resp:
            token = (await resp.json()).get('access_token')

        headers = {'Authorization': f'Bearer {token}'}
        async with session.get(f'{VLM_AUTH_API}api/v2/clients/{client_id}', headers=headers) as resp:
            if resp.status != 200:
                raise web.HTTPForbidden(reason='Invalid Client ID')
            return await resp.json()
