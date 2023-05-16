from aiohttp import web

from hail_search.search import search_hail_backend


async def search(request: web.Request) -> web.Response:
    hail_results, total_results = search_hail_backend(await request.json())
    return web.json_response({'results': hail_results, 'total': total_results})


def run():
    app = web.Application()
    app.add_routes([web.post("/search", search)])
    web.run_app(
        app,
        host="0.0.0.0",
        port=5000,
    )


run()
