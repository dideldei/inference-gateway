"""API key authentication, request size limits, and request ID middleware."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings
from app.logging import generate_request_id, request_id_var

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and log request lifecycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = generate_request_id()
        request.state.request_id = rid
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            logger.info("%s %s", request.method, request.url.path)
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "%s %s -> %s (%.0f ms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Enforce Bearer token authentication when API_KEY is configured.

    The /health endpoint is always accessible without authentication.
    """

    def __init__(self, app, api_key: str | None) -> None:  # noqa: ANN001
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self.api_key is None:
            return await call_next(request)

        # /health is always public
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": {"type": "auth_required", "message": "Missing or malformed Authorization header. Expected: Bearer <API_KEY>"}},
            )

        provided_key = auth_header[len("Bearer "):]
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={"error": {"type": "auth_failed", "message": "Invalid API key"}},
            )

        return await call_next(request)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds a configured limit.

    Only enforced on POST requests to audio convenience endpoints.
    """

    def __init__(self, app, max_bytes: int) -> None:  # noqa: ANN001
        super().__init__(app)
        self.max_bytes = max_bytes
        self._guarded_paths = {"/v1/transcribe", "/v1/analyze"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "POST" and request.url.path in self._guarded_paths:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > self.max_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": {
                                    "type": "request_too_large",
                                    "message": f"Request body exceeds maximum allowed size ({self.max_bytes} bytes)",
                                }
                            },
                        )
                except ValueError:
                    pass  # non-integer content-length; let downstream handle

        return await call_next(request)
