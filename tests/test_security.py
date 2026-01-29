"""Tests for security middleware: API key auth, request size limits, request ID."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.security import APIKeyMiddleware, MaxBodySizeMiddleware, RequestIDMiddleware


# ---------------------------------------------------------------------------
# Helpers – build minimal FastAPI apps with specific middleware for isolation
# ---------------------------------------------------------------------------

def _make_app_with_api_key(api_key: str | None) -> FastAPI:
    """Create a minimal app with APIKeyMiddleware configured."""
    test_app = FastAPI()
    test_app.add_middleware(APIKeyMiddleware, api_key=api_key)

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    @test_app.post("/v1/chat/completions")
    async def chat():
        return {"result": "ok"}

    @test_app.get("/v1/models")
    async def models():
        return {"data": []}

    @test_app.post("/v1/transcribe")
    async def transcribe():
        return {"transcript": "hello"}

    return test_app


def _make_app_with_body_limit(max_bytes: int) -> FastAPI:
    """Create a minimal app with MaxBodySizeMiddleware configured."""
    from fastapi import Request

    test_app = FastAPI()
    test_app.add_middleware(MaxBodySizeMiddleware, max_bytes=max_bytes)

    @test_app.post("/v1/transcribe")
    async def transcribe(request: Request):
        await request.body()
        return {"transcript": "hello"}

    @test_app.post("/v1/analyze")
    async def analyze(request: Request):
        await request.body()
        return {"result": "ok"}

    @test_app.post("/v1/chat/completions")
    async def chat(request: Request):
        await request.body()
        return {"result": "ok"}

    return test_app


def _make_app_with_request_id() -> FastAPI:
    """Create a minimal app with RequestIDMiddleware configured."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    return test_app


# ---------------------------------------------------------------------------
# API Key Middleware Tests
# ---------------------------------------------------------------------------

class TestAPIKeyMiddleware:
    """Tests for API key enforcement."""

    def test_no_api_key_configured_allows_all(self):
        """When API_KEY is not set, all requests pass through."""
        client = TestClient(_make_app_with_api_key(None))

        assert client.get("/health").status_code == 200
        assert client.post("/v1/chat/completions").status_code == 200
        assert client.get("/v1/models").status_code == 200
        assert client.post("/v1/transcribe").status_code == 200

    def test_health_always_public(self):
        """The /health endpoint is accessible without auth even when API_KEY is set."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_missing_auth_header_returns_401(self):
        """Requests without Authorization header return 401."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        resp = client.post("/v1/chat/completions")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["type"] == "auth_required"

    def test_wrong_auth_scheme_returns_401(self):
        """Non-Bearer auth schemes return 401."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        resp = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["type"] == "auth_required"

    def test_wrong_api_key_returns_401(self):
        """An incorrect Bearer token returns 401."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        resp = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["type"] == "auth_failed"

    def test_correct_api_key_allows_request(self):
        """A correct Bearer token allows the request through."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        resp = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer secret-key"},
        )
        assert resp.status_code == 200

    def test_auth_required_on_models(self):
        """GET /v1/models also requires auth when API_KEY is set."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        assert client.get("/v1/models").status_code == 401
        resp = client.get("/v1/models", headers={"Authorization": "Bearer secret-key"})
        assert resp.status_code == 200

    def test_auth_required_on_transcribe(self):
        """POST /v1/transcribe also requires auth when API_KEY is set."""
        client = TestClient(_make_app_with_api_key("secret-key"))

        assert client.post("/v1/transcribe").status_code == 401
        resp = client.post("/v1/transcribe", headers={"Authorization": "Bearer secret-key"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Max Body Size Middleware Tests
# ---------------------------------------------------------------------------

class TestMaxBodySizeMiddleware:
    """Tests for upload size limits on audio endpoints."""

    def test_small_upload_allowed(self):
        """Uploads under the limit pass through."""
        client = TestClient(_make_app_with_body_limit(1000))

        resp = client.post(
            "/v1/transcribe",
            content=b"x" * 500,
            headers={"Content-Length": "500"},
        )
        assert resp.status_code == 200

    def test_oversized_upload_rejected_transcribe(self):
        """Uploads over the limit on /v1/transcribe return 413."""
        client = TestClient(_make_app_with_body_limit(100))

        resp = client.post(
            "/v1/transcribe",
            content=b"x" * 200,
            headers={"Content-Length": "200"},
        )
        assert resp.status_code == 413
        assert resp.json()["error"]["type"] == "request_too_large"

    def test_oversized_upload_rejected_analyze(self):
        """Uploads over the limit on /v1/analyze return 413."""
        client = TestClient(_make_app_with_body_limit(100))

        resp = client.post(
            "/v1/analyze",
            content=b"x" * 200,
            headers={"Content-Length": "200"},
        )
        assert resp.status_code == 413

    def test_chat_completions_not_guarded(self):
        """POST /v1/chat/completions is not subject to audio upload limits."""
        client = TestClient(_make_app_with_body_limit(100))

        resp = client.post(
            "/v1/chat/completions",
            content=b"x" * 200,
            headers={"Content-Length": "200"},
        )
        assert resp.status_code == 200

    def test_no_content_length_passes(self):
        """Requests without Content-Length header are not rejected."""
        client = TestClient(_make_app_with_body_limit(100))

        # TestClient may add content-length automatically; this tests the logic path
        resp = client.post("/v1/transcribe", content=b"")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Request ID Middleware Tests
# ---------------------------------------------------------------------------

class TestRequestIDMiddleware:
    """Tests for request ID injection."""

    def test_response_has_request_id_header(self):
        """Every response should include an X-Request-ID header."""
        client = TestClient(_make_app_with_request_id())

        resp = client.get("/health")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        rid = resp.headers["x-request-id"]
        assert len(rid) == 12  # hex[:12]

    def test_request_ids_are_unique(self):
        """Each request gets a distinct ID."""
        client = TestClient(_make_app_with_request_id())

        ids = {client.get("/health").headers["x-request-id"] for _ in range(10)}
        assert len(ids) == 10


# ---------------------------------------------------------------------------
# Integration: security with the real app
# ---------------------------------------------------------------------------

class TestSecurityIntegration:
    """Test that middleware is wired correctly in the actual app."""

    def test_health_accessible_without_auth(self):
        """The real app's /health endpoint works without auth."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_response_includes_request_id(self):
        """The real app attaches X-Request-ID to responses."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
