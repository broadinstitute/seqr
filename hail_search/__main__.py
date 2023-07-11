from aiohttp import web
import hail as hl
import logging


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def run():
    logging.basicConfig(level=logging.INFO)
    hl.init()
    app = web.Application()
    app.add_routes([
        web.get('/status', status),
    ])
    web.run_app(
        app,
        host='0.0.0.0',
        port=5000,
        access_log_format='%{From}i "%r" %s %Tfs',
    )


run()
