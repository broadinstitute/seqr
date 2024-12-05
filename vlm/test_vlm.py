from aiohttp.test_utils import AioHTTPTestCase

from vlm.web_app import init_web_app


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

    async def test_match(self):
        async with self.client.request('GET', '/vlm/match?assemblyId=GRCh38&referenceName=1&start=38724419&referenceBases=T&alternateBases=G') as resp:
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
        async with self.client.request('GET', '/vlm/match?assemblyId=hg19&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', '/vlm/match?assemblyId=GRCh38&referenceName=chr7&start=143573079&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G') as resp:
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

    async def test_match_error(self):
        async with self.client.request('GET', '/vlm/match') as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(
                resp.reason,
                'Missing required parameters: assemblyId, referenceName, start, referenceBases, alternateBases',
            )

        async with self.client.request('GET', '/vlm/match?assemblyId=38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid assemblyId: 38')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=27&start=143270172&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid referenceName: 27')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=7&start=1x43270172&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 1x43270172')

        async with self.client.request('GET', '/vlm/match?assemblyId=hg38&referenceName=7&start=999999999&referenceBases=A&alternateBases=G') as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 999999999')