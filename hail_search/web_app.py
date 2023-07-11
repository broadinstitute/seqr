from aiohttp import web
import hail as hl
import logging


async def status(request: web.Request) -> web.Response:
    return web.json_response({'success': True})


def init_web_app():
    logging.basicConfig(level=logging.INFO)
    #hl.init()
    app = web.Application()
    app.add_routes([
        web.get('/status', status),
    ])
    return app
