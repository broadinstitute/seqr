from aiohttp import web

from loading_pipeline.api.app import init_web_app
from loading_pipeline.lib.logger import get_logger


def run():
    app = init_web_app()
    logger = get_logger(__name__)
    web.run_app(
        app,
        host='0.0.0.0',  # noqa: S104
        port=6000,
        access_log=logger,
    )


run()
