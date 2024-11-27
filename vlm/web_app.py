from aiohttp import web
import hail as hl
import logging
import os
import traceback

from vlm.match import get_variant_match

logger = logging.getLogger(__name__)

JAVA_OPTS_XSS = os.environ.get('JAVA_OPTS_XSS')
MACHINE_MEM = os.environ.get('MACHINE_MEM')


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


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


async def match(request: web.Request) -> web.Response:
    variant_match = get_variant_match(request.query)
    return web.json_response({'variant_match': variant_match})


async def init_web_app():
    spark_conf = {}
    # memory limits adapted from https://github.com/hail-is/hail/blob/main/hail/python/hailtop/hailctl/dataproc/start.py#L321C17-L321C36
    if MACHINE_MEM:
        spark_conf['spark.driver.memory'] = f'{int((int(MACHINE_MEM) - 11) * JVM_MEMORY_FRACTION)}g'
    if JAVA_OPTS_XSS:
        spark_conf.update(
            {f'spark.{field}.extraJavaOptions': f'-Xss{JAVA_OPTS_XSS}' for field in ['driver', 'executor']})
    hl.init(idempotent=True, spark_conf=spark_conf or None,
            backend='local',  # TODO testing only
            )

    app = web.Application(middlewares=[error_middleware], client_max_size=(1024 ** 2) * 10)
    app.add_routes([
        web.get('/vlm/match', match),
        web.get('/vlm/status', status),
    ])
    return app
