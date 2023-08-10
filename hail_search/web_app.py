from aiohttp import web
import json
import hail as hl

from hail_search.search import search_hail_backend, load_globals

APP_GLOBALS = 'APP_GLOBALS'


def _hl_json_default(o):
    if isinstance(o, hl.Struct) or isinstance(o, hl.utils.frozendict):
        return dict(o)


def hl_json_dumps(obj):
    return json.dumps(obj, default=_hl_json_default)


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = search_hail_backend(await request.json(), request.app[APP_GLOBALS])
    return web.json_response({'results': hail_results, 'total': total_results}, dumps=hl_json_dumps)


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def init_web_app():
    app = web.Application()
    app.add_routes([
        web.get('/status', status),
        web.post('/search', search),
    ])
    app[APP_GLOBALS] = load_globals()
    return app
