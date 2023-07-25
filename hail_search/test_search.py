from aiohttp.test_utils import AioHTTPTestCase
from copy import deepcopy

from hail_search.web_app import init_web_app


class HailSearchTestCase(AioHTTPTestCase):

    async def get_application(self):
        return init_web_app()

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})
