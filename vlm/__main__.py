from aiohttp import web
import logging

from vlm.web_app import init_web_app


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def run():
    logging.basicConfig(level=logging.INFO)
    app = init_web_app()
    web.run_app(
        app,
        host='0.0.0.0',  # nosec
        port=7000,
        access_log_format='%a "%r" %s %Tfs',
    )


run()
