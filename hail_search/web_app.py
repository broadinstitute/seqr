from aiohttp import web
import hail as hl
import logging

from hail_search.search import search_hail_backend


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = search_hail_backend(await request.json())
    return web.json_response({'results': hail_results, 'total': total_results})


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def init_web_app():
    logging.basicConfig(level=logging.INFO)
    hl.init()
    app = web.Application()
    app.add_routes([
        web.get('/status', status),
        web.post('/search', search),
    ])
    return app
