"""Per-request tracking: a correlation id bound to every log line of the request.

Written as pure ASGI on purpose. Starlette's `BaseHTTPMiddleware` buffers the
response body, which would defeat the SSE streaming endpoints; a raw ASGI wrapper
leaves the stream untouched while still stamping the id and timing the request.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from loguru import logger

REQUEST_ID_HEADER = b"x-request-id"


class RequestContextMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(REQUEST_ID_HEADER)
        request_id = incoming.decode() if incoming else uuid.uuid4().hex

        method = scope.get("method", "")
        path = scope.get("path", "")
        started = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                message.setdefault("headers", []).append((REQUEST_ID_HEADER, request_id.encode()))
            await send(message)

        with logger.contextualize(request_id=request_id):
            logger.info("→ {} {}", method, path)
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception:
                logger.exception("✗ {} {} raised", method, path)
                raise
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info("← {} {} {} ({:.1f}ms)", method, path, status["code"], elapsed_ms)
