from aiohttp import web

from hail_search.web_app import init_web_app


def run():
    app = init_web_app()
    web.run_app(
        app,
        host='0.0.0.0',  # nosec
        port=5000,
        access_log_format='%{From}i "%r" %s %Tfs',
    )


if __name__ == "__main__":
    run()
