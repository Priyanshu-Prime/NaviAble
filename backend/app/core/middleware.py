"""Request-correlation middleware.

Reads ``X-Request-ID`` from the inbound request, generating a fresh UUID4
when absent. The ID is stashed on ``request.state.request_id`` for handlers,
echoed back on the response, and bound into the contextvar that the logging
formatter reads — so every log line emitted while handling the request is
tagged with the same ID.
"""

from __future__ import annotations

import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def get_request_id() -> str:
    """Return the request ID for the current async context, or '-'."""
    return _request_id_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(self.HEADER) or str(uuid.uuid4())
        token = _request_id_var.set(rid)
        request.state.request_id = rid
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers[self.HEADER] = rid
        return response
