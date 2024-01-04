from aiohttp import web
import json
import hail as hl
import logging

from hail_search.search import search_hail_backend, load_globals, lookup_variant

logger = logging.getLogger(__name__)


def _handle_exception(e, request):
    logger.error(f'{request.headers.get("From")} "{e}"')
    raise e


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPError as e:
        _handle_exception(e, request)
    except Exception as e:
        _handle_exception(web.HTTPInternalServerError(reason=str(e)), request)


def _hl_json_default(o):
    if isinstance(o, hl.Struct) or isinstance(o, hl.utils.frozendict):
        return dict(o)
    elif isinstance(o, set):
        return sorted(o)


def hl_json_dumps(obj):
    return json.dumps(obj, default=_hl_json_default)


async def gene_counts(request: web.Request) -> web.Response:
    return web.json_response(search_hail_backend(await request.json(), gene_counts=True), dumps=hl_json_dumps)


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = search_hail_backend(await request.json())
    return web.json_response({'results': hail_results, 'total': total_results}, dumps=hl_json_dumps)


async def lookup(request: web.Request) -> web.Response:
    return web.json_response(lookup_variant(await request.json()), dumps=hl_json_dumps)


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


async def init_web_app():
    hl.init(idempotent=True)
    load_globals()
    app = web.Application(middlewares=[error_middleware], client_max_size=(1024**2)*10)
    app.add_routes([
        web.get('/status', status),
        web.post('/search', search),
        web.post('/gene_counts', gene_counts),
        web.post('/lookup', lookup),
    ])
    return app
