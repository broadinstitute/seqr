from aiohttp import web
import asyncio
import concurrent.futures
import functools
import json
import os
import hail as hl
import logging
import traceback

from hail_search.search import search_hail_backend, load_globals, lookup_variant

loop = asyncio.get_event_loop()
logger = logging.getLogger(__name__)

JAVA_OPTS_XSS = os.environ.get('JAVA_OPTS_XSS')
MACHINE_MEM = os.environ.get('MACHINE_MEM')
JVM_MEMORY_FRACTION = 0.9


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
        error_reason = f'{e}: {traceback.format_exc()}'
        _handle_exception(web.HTTPInternalServerError(reason=error_reason), request)


def _hl_json_default(o):
    if isinstance(o, hl.Struct) or isinstance(o, hl.utils.frozendict):
        return dict(o)
    elif isinstance(o, set):
        return sorted(o)


def hl_json_dumps(obj):
    return json.dumps(obj, default=_hl_json_default)


async def gene_counts(request: web.Request) -> web.Response:
    hail_results = await loop.run_in_executor(request.app.pool, functools.partial(search_hail_backend, await request.json(), gene_counts=True))
    return web.json_response(hail_results, dumps=hl_json_dumps)


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = await loop.run_in_executor(request.app.pool, functools.partial(search_hail_backend, await request.json()))
    return web.json_response({'results': hail_results, 'total': total_results}, dumps=hl_json_dumps)


async def lookup(request: web.Request) -> web.Response:
    result = await loop.run_in_executor(request.app.pool, functools.partial(lookup_variant, await request.json()))
    return web.json_response(result, dumps=hl_json_dumps)


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


async def init_web_app():
    spark_conf = {}
    # memory limits adapted from https://github.com/hail-is/hail/blob/main/hail/python/hailtop/hailctl/dataproc/start.py#L321C17-L321C36
    if MACHINE_MEM:
        spark_conf['spark.driver.memory'] = f'{int((int(MACHINE_MEM)-11)*JVM_MEMORY_FRACTION)}g'
    if JAVA_OPTS_XSS:
        spark_conf.update({f'spark.{field}.extraJavaOptions': f'-Xss{JAVA_OPTS_XSS}' for field in ['driver', 'executor']})
    hl.init(idempotent=True, spark_conf=spark_conf or None)
    hl._set_flags(use_new_shuffle='1')
    load_globals()
    app = web.Application(middlewares=[error_middleware], client_max_size=(1024**2)*10)
    app.add_routes([
        web.get('/status', status),
        web.post('/search', search),
        web.post('/gene_counts', gene_counts),
        web.post('/lookup', lookup),
    ])
    # The idea here is to run the hail queries off the main thread so that the
    # event loop stays live for the /status check to be responsive.  We only
    # run a single thread though so that hail queries block hail queries.
    app.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    return app
