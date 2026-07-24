from httpx import ASGITransport, AsyncClient
from loguru import logger
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _client():
    async def ok(_request):
        # Emitted inside the request scope, so it must carry the bound request_id.
        logger.info("handling")
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/ping", ok)])
    # Imported here so the middleware is applied to a fresh app per client.
    from arp.api.middleware import RequestContextMiddleware

    app.add_middleware(RequestContextMiddleware)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_generates_a_request_id_when_absent():
    response = await _client().get("/ping")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


async def test_propagates_an_incoming_request_id():
    response = await _client().get("/ping", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


async def test_request_id_is_bound_to_the_log_context():
    seen = []
    handler_id = logger.add(seen.append, level="INFO", filter=lambda r: r["message"] == "handling")
    try:
        await _client().get("/ping", headers={"X-Request-ID": "trace-xyz"})
    finally:
        logger.remove(handler_id)
    assert seen
    assert seen[0].record["extra"]["request_id"] == "trace-xyz"
