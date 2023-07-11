from aiohttp import web
import hail as hl
import logging

from hail_search.web_app import init_web_app


def run():
    app = init_web_app()
    web.run_app(
        app,
        host='0.0.0.0',
        port=5000,
        access_log_format='%{From}i "%r" %s %Tfs',
    )


run()
