"""FastAPI application entry point for the Inference Gateway."""

import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.forwarder import UpstreamTimeoutError, UpstreamUnreachableError, forward_chat_completion, forward_models
from app.routing import select_upstream_url
from app.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Inference Gateway",
    description="OpenAI-compatible inference gateway with optional audio preprocessing and routing",
    version=__version__,
)

# CORS middleware - restricted by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # Will be configured via environment variables in T1
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True, "version": __version__}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    """
    OpenAI-compatible chat completions endpoint.
    
    Forwards requests to upstream backend based on routing configuration.
    """
    settings = get_settings()
    
    try:
        # Read and parse request body
        body_bytes = await request.body()
        try:
            request_body = json.loads(body_bytes)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"type": "invalid_json", "message": f"Invalid JSON in request body: {str(e)}"}},
            )
        
        # Validate it's a dict/object
        if not isinstance(request_body, dict):
            raise HTTPException(
                status_code=400,
                detail={"error": {"type": "invalid_request", "message": "Request body must be a JSON object"}},
            )
        
        # Select upstream URL based on routing rules
        try:
            base_url = select_upstream_url(request_body, settings)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail={"error": {"type": "configuration_error", "message": str(e)}},
            )
        
        # Forward request to upstream
        try:
            upstream_response = await forward_chat_completion(request_body, base_url, settings)
        except UpstreamUnreachableError as e:
            error_response = ErrorResponse(
                error=ErrorDetail(type="upstream_unreachable", message=e.message),
                upstream=e.upstream,
            )
            raise HTTPException(status_code=502, detail=error_response.model_dump())
        except UpstreamTimeoutError as e:
            error_response = ErrorResponse(
                error=ErrorDetail(type="upstream_timeout", message=e.message),
                upstream=e.upstream,
            )
            raise HTTPException(status_code=504, detail=error_response.model_dump())
        
        # Return upstream response transparently
        # Try to parse as JSON, but if it fails, return as-is
        try:
            response_body = upstream_response.json()
            # Serialize back to JSON bytes for Response
            content = json.dumps(response_body).encode("utf-8")
            media_type = "application/json"
        except (json.JSONDecodeError, ValueError):
            # Non-JSON response - pass through as-is
            content = upstream_response.content
            media_type = upstream_response.headers.get("content-type", "application/octet-stream")
        
        return Response(
            content=content,
            status_code=upstream_response.status_code,
            media_type=media_type,
            headers={
                # Preserve upstream headers where appropriate
                key: value
                for key, value in upstream_response.headers.items()
                if key.lower() not in ("content-length", "content-encoding", "transfer-encoding")
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in chat_completions: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"type": "internal_error", "message": "An unexpected error occurred"}},
        )


@app.get("/v1/models")
async def models() -> Response:
    """
    OpenAI-compatible models list endpoint.
    
    Forwards request to upstream backend. In audio_text mode, defaults to TEXT upstream.
    """
    settings = get_settings()
    
    # Select upstream URL
    if settings.routing_mode == "single":
        base_url = settings.effective_base_url
        if not base_url:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "type": "configuration_error",
                        "message": "No upstream URL configured. Please set DEFAULT_BASE_URL or TEXT_BASE_URL.",
                    }
                },
            )
    elif settings.routing_mode == "audio_text":
        # Default to TEXT upstream for /v1/models (as per T2 spec: "keep it simple")
        base_url = settings.text_base_url
        if not base_url:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "type": "configuration_error",
                        "message": "TEXT_BASE_URL is required for /v1/models endpoint.",
                    }
                },
            )
    else:
        raise HTTPException(
            status_code=500,
            detail={"error": {"type": "configuration_error", "message": f"Unknown routing mode: {settings.routing_mode}"}},
        )
    
    # Forward request to upstream
    try:
        upstream_response = await forward_models(base_url, settings)
    except UpstreamUnreachableError as e:
        error_response = ErrorResponse(
            error=ErrorDetail(type="upstream_unreachable", message=e.message),
            upstream=e.upstream,
        )
        raise HTTPException(status_code=502, detail=error_response.model_dump())
    except UpstreamTimeoutError as e:
        error_response = ErrorResponse(
            error=ErrorDetail(type="upstream_timeout", message=e.message),
            upstream=e.upstream,
        )
        raise HTTPException(status_code=504, detail=error_response.model_dump())
    
    # Return upstream response transparently
    try:
        response_body = upstream_response.json()
        # Serialize back to JSON bytes for Response
        content = json.dumps(response_body).encode("utf-8")
        media_type = "application/json"
    except (json.JSONDecodeError, ValueError):
        # Non-JSON response - pass through as-is
        content = upstream_response.content
        media_type = upstream_response.headers.get("content-type", "application/octet-stream")
    
    return Response(
        content=content,
        status_code=upstream_response.status_code,
        media_type=media_type,
        headers={
            # Preserve upstream headers where appropriate
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() not in ("content-length", "content-encoding", "transfer-encoding")
        },
    )


# Router registration placeholders for future endpoints:
# - POST /v1/transcribe (T5)
# - POST /v1/analyze (T6)
