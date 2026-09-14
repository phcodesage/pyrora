"""Useful default HTTP middleware and their plugin-friendly API types."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to request state and response headers."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get(self.header_name) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Set a non-authoritative processing-time response header."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.6f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set conservative baseline headers without imposing a CSP policy."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response
