from aiohttp import web
import hail as hl
import logging
import os
import traceback

from vlm.match import get_variant_match, GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37

logger = logging.getLogger(__name__)

JAVA_OPTS_XSS = os.environ.get('JAVA_OPTS_XSS')
MACHINE_MEM = os.environ.get('MACHINE_MEM')
JVM_MEMORY_FRACTION = 0.9

LIFTOVER_DIR = f'{os.path.dirname(os.path.abspath(__file__))}/liftover_references'


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
    return web.json_response(get_variant_match(request.query))


async def init_web_app():
    spark_conf = {}
    # memory limits adapted from https://github.com/hail-is/hail/blob/main/hail/python/hailtop/hailctl/dataproc/start.py#L321C17-L321C36
    if MACHINE_MEM:
        spark_conf['spark.driver.memory'] = f'{int((int(MACHINE_MEM) - 11) * JVM_MEMORY_FRACTION)}g'
    if JAVA_OPTS_XSS:
        spark_conf.update(
            {f'spark.{field}.extraJavaOptions': f'-Xss{JAVA_OPTS_XSS}' for field in ['driver', 'executor']})
    hl.init(idempotent=True, spark_conf=spark_conf or None)

    rg37 = hl.get_reference(GENOME_VERSION_GRCh37)
    rg38 = hl.get_reference(GENOME_VERSION_GRCh38)
    if not rg37.has_liftover(rg38):
        rg37.add_liftover(f'{LIFTOVER_DIR}/grch37_to_grch38.over.chain.gz', rg38)
    if not rg38.has_liftover(rg37):
        rg38.add_liftover(f'{LIFTOVER_DIR}/grch38_to_grch37.over.chain.gz', rg37)

    app = web.Application(middlewares=[error_middleware], client_max_size=(1024 ** 2) * 10)
    app.add_routes([
        web.get('/vlm/match', match),
        web.get('/vlm/status', status),
    ])
    return app
