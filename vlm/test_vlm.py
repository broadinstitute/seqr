from aiohttp.test_utils import AioHTTPTestCase
from aioresponses import aioresponses
import jwt
import logging
import pytest

from vlm.web_app import init_web_app

REQUESTER_CLIENT_ID = 'abc123'

class VlmTestCase(AioHTTPTestCase):

    async def get_application(self):
        return await init_web_app()

    async def test_error(self):
        async with self.client.request('GET', '/foo') as resp:
            self.assertEqual(resp.status, 404)

    async def test_status(self):
        async with self.client.request('GET', '/vlm/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        caplog.set_level(logging.INFO)
        self._caplog = caplog

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match(self, mocked_responses):

        mocked_responses.post(
            'https://vlm-auth.us.auth0.com/oauth/token', payload={'access_token': 'test_token'}, repeat=True,
        )
        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            payload={'tenant': 'vlm-auth', 'name': 'Test Node'},
            repeat=True,
        )
        jwt_body = {'iss': 'https://vlm-auth.us.auth0.com/', 'azp': REQUESTER_CLIENT_ID}
        headers = {'Authorization': f'Bearer {jwt.encode(jwt_body, "")}'}

        async with self.client.request('GET', '/vlm/match?assemblyId=GRCh38&referenceName=1&start=38724419&referenceBases=T&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/summary_data/variant_lookup?genomeVersion=38&variantId=chr1-38724419-T-G',
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 30,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM Homozygous',
                        'results': [],
                        'resultsCount': 7,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': True,
                        'id': 'TestVLM Heterozygous',
                        'results': [],
                        'resultsCount': 23,
                        'setType': 'genomicVariant'
                    },
                ],
            }
        })
        mocked_responses.assert_called_with(
            'https://vlm-auth.us.auth0.com/oauth/token',
            method='POST',
            json={'client_id': 'unknown_client_id', 'client_secret': 'unknown_client_secret', 'audience': 'https://vlm-auth.us.auth0.com/api/v2/', 'grant_type': 'client_credentials'},
        )
        mocked_responses.assert_called_with(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            headers={'Authorization': 'Bearer test_token'},
        )
        self.assertIn(
            'Received match request from Test Node: assemblyId=GRCh38&referenceName=1&start=38724419&referenceBases=T&alternateBases=G',
            self._caplog.messages,
        )

        only_37_response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/summary_data/variant_lookup?genomeVersion=37&variantId=7-143270172-A-G',
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 3203,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM Homozygous',
                        'results': [],
                        'resultsCount': 1508,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': True,
                        'id': 'TestVLM Heterozygous',
                        'results': [],
                        'resultsCount': 1695,
                        'setType': 'genomicVariant'
                    },
                ],
            }
        }
        async with self.client.request('GET', '/vlm/match?assemblyId=hg19&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', '/vlm/match?assemblyId=GRCh38&referenceName=chr7&start=143573079&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/summary_data/variant_lookup?genomeVersion=38&variantId=chr7-143270172-A-G',
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': False,
                'total': 0,
            },
            'response': {
                'resultSets': [],
            }
        })

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match_error(self, mocked_responses):
        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}', status=404,
        )

        async with self.client.request('GET', '/vlm/match') as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid authorization header')

        headers = {'Authorization': 'token'}
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid authorization header')

        headers['Authorization'] =  'JWT token'
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token scheme')

        headers['Authorization'] = 'Bearer token'
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Not enough segments')

        jwt_body = {'iss': 'invalid_issuer'}
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Token is missing the "azp" claim')

        jwt_body['azp'] = REQUESTER_CLIENT_ID
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Invalid issuer')

        mocked_responses.post('https://vlm-auth.us.auth0.com/oauth/token', status=400, payload={'error': 'invalid_request'})
        jwt_body['iss'] = 'https://vlm-auth.us.auth0.com/'
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Credential Check Error')
        self.assertEqual(self._caplog.messages[-3], "Credential Check Error: 400 - {'error': 'invalid_request'}")

        mocked_responses.post('https://vlm-auth.us.auth0.com/oauth/token', payload={'access_token': 'test_token'}, repeat=True)
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid Client ID abc123')
        self.assertEqual(self._caplog.messages[-3], "Invalid Client ID abc123: 404 - Not Found")

        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            payload={'tenant': 'vlm-auth'},
            repeat=True,
        )
        async with self.client.request('GET', '/vlm/match', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(
                resp.reason,
                'Missing required parameters: assemblyId, referenceName, start, referenceBases, alternateBases',
            )

        async with self.client.request('GET', '/vlm/match?assemblyId=38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid assemblyId: 38')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=27&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid referenceName: 27')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=7&start=1x43270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 1x43270172')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=7&start=999999999&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 999999999')