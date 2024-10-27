from aiohttp import web
import logging
import traceback

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
        error_reason = f'{e}: {traceback.format_exc()}'
        _handle_exception(web.HTTPInternalServerError(reason=error_reason), request)


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def run():
    logging.basicConfig(level=logging.INFO)
    app = web.Application(middlewares=[error_middleware], client_max_size=(1024 ** 2) * 10)
    app.add_routes([
        web.get('/status', status),
    ])
    web.run_app(
        app,
        host='0.0.0.0',  # nosec
        port=6000,
        access_log_format='%a "%r" %s %Tfs',
    )


run()
