from aiohttp.test_utils import AioHTTPTestCase

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    VARIANT1, VARIANT2, VARIANT3, VARIANT4
from hail_search.web_app import init_web_app


class HailSearchTestCase(AioHTTPTestCase):

    async def get_application(self):
        return init_web_app()

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    async def test_search(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertSetEqual(set(resp_json.keys()), {'results', 'total'})
        self.assertEqual(resp_json['total'], 4)
        results = [VARIANT1, VARIANT2, VARIANT3, VARIANT4]
        self.assertListEqual(
            [v['variantId'] for v in resp_json['results']], [v['variantId'] for v in results]
        )
        self.assertListEqual(resp_json['results'], results)

    async def test_search_missing_data(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            text = await resp.text()
        self.assertEqual(text, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')
