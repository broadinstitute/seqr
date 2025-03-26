from aiohttp import web
import asyncio
import concurrent.futures
import ctypes
import functools
import json
import os
import hail as hl
import logging
import traceback
from typing import Callable

from hail_search.search import search_hail_backend, load_globals, lookup_variant, lookup_variants

logger = logging.getLogger(__name__)

JAVA_OPTS_XSS = os.environ.get('JAVA_OPTS_XSS')
MACHINE_MEM = os.environ.get('MACHINE_MEM')
JVM_MEMORY_FRACTION = 0.9
QUERY_TIMEOUT_S = 300


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

async def sync_to_async_hail_query(request: web.Request, query: Callable, *args, timeout_s=QUERY_TIMEOUT_S, **kwargs):
    request_body = None
    if request.body_exists:
        request_body = await request.json()

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(request.app.pool, functools.partial(query, request_body, *args, **kwargs))
    try:
        return await asyncio.wait_for(future, timeout_s)
    except asyncio.TimeoutError:
        # Well documented issue with the "wait_for" approach.... the concurrent.Future is canceled but
        # the underlying thread is not, allowing the Hail Query under the hood to keep running.
        # https://stackoverflow.com/questions/34452590/timeout-handling-while-using-run-in-executor-and-asyncio
        # This unsafe approach is taken from:
        # https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread
        #
        # A few other thoughts:
        # - A ProcessPoolExecutor instead of a ThreadPoolExecutor would allow for safe worker termination
        # and would potentially be a safer option in general (some portion of a hail query is cpu bound in python!)
        # - A "timeout" decorator applied to the query function, catching a SIGALARM would also potentially
        # suffice... but threads don't play well with signals.
        # - We could also just kill the service/pod (which is fine).
        for t in request.app.pool._threads:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(t.ident), ctypes.py_object(TimeoutError))
            if res > 1:
                # "if it returns a number greater than one, you're in trouble,
                # and you should call it again with exc=NULL to revert the effect"
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(t.ident), None)
                raise SystemExit('PyThreadState_SetAsyncExc failed')
        raise TimeoutError('Hail Query Timeout Exceeded')

async def gene_counts(request: web.Request) -> web.Response:
    hail_results = await sync_to_async_hail_query(request, search_hail_backend, gene_counts=True)
    return web.json_response(hail_results, dumps=hl_json_dumps)


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = await sync_to_async_hail_query(request, search_hail_backend)
    return web.json_response({'results': hail_results, 'total': total_results}, dumps=hl_json_dumps)


async def lookup(request: web.Request) -> web.Response:
    result = await sync_to_async_hail_query(request, lookup_variant)
    return web.json_response(result, dumps=hl_json_dumps)


async def multi_lookup(request: web.Request) -> web.Response:
    result = await sync_to_async_hail_query(request, lookup_variants)
    return web.json_response({'results': result}, dumps=hl_json_dumps)


async def reload_globals(request: web.Request) -> web.Response:
    result = await sync_to_async_hail_query(request, lambda _: load_globals())
    return web.json_response(
        result,
        dumps=hl_json_dumps
    )


async def status(request: web.Request) -> web.Response:
    # Make sure the hail backend process is still alive.
    await sync_to_async_hail_query(request, lambda _: hl.eval(1 + 1))
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
    app = web.Application(middlewares=[error_middleware], client_max_size=(1024**2)*20)
    app.add_routes([
        web.get('/status', status),
        web.post('/reload_globals', reload_globals),
        web.post('/search', search),
        web.post('/gene_counts', gene_counts),
        web.post('/lookup', lookup),
        web.post('/multi_lookup', multi_lookup),
    ])
    # The idea here is to run the hail queries off the main thread so that the
    # event loop stays live and the /status check is responsive.  We only
    # run a single thread, though, so that hail queries block hail queries
    # and we never run more than a single hail query at a time.
    app.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    return app
