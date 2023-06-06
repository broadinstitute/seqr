from aiohttp import web
import hail as hl
import logging

from hail_search.search import search_hail_backend


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = search_hail_backend(await request.json())
    return web.json_response({'results': hail_results, 'total': total_results})


def run():
    logging.basicConfig(level=logging.INFO)
    hl.init()
    app = web.Application()
    app.add_routes([web.post("/search", search)])
    # TODO add gene_counts route
    web.run_app(
        app,
        host="0.0.0.0",
        port=5000,
        access_log_format='"%r" %s %b seconds:%Tf',
    )


run()
