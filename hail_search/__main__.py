from aiohttp import web

from hail_search.web_app import init_web_app

"""
1-11794419-T-G
1-91511686-T-G
1-10439-AC-A
1-10146-ACC-A
1-94818-T-C
"""

def run():
    app = init_web_app()
    web.run_app(
        app,
        host='0.0.0.0',  # nosec
        port=5000,
        access_log_format='%{From}i "%r" %s %Tfs',
    )


run()
