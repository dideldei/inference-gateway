"""FastAPI application entry point for the Inference Gateway."""

import base64
import json
import logging
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.audio import AudioPreprocessError, normalize_audio_to_wav
from app.config import get_settings
from app.forwarder import UpstreamTimeoutError, UpstreamUnreachableError, forward_chat_completion, forward_models
from app.logging import setup_logging
from app.routing import select_upstream_url
from app.schemas import AnalyzeResponse, ErrorDetail, ErrorResponse, TranscribeResponse
from app.security import APIKeyMiddleware, MaxBodySizeMiddleware, RequestIDMiddleware

logger = logging.getLogger(__name__)


def _load_settings_safe():
    """Load settings, returning defaults suitable for middleware when config is unavailable (e.g. tests)."""
    try:
        return get_settings()
    except (ValueError, Exception):
        return None


def create_app() -> FastAPI:
    """Build and return the FastAPI application with all middleware configured."""
    settings = _load_settings_safe()

    if settings is not None:
        setup_logging(settings.log_level)

    application = FastAPI(
        title="Inference Gateway",
        description="OpenAI-compatible inference gateway with optional audio preprocessing and routing",
        version=__version__,
    )

    # Middleware stack (order matters: outermost is listed first, executes first)
    # 1. Request ID — assigned before anything else
    application.add_middleware(RequestIDMiddleware)

    # 2. API key enforcement (skips /health)
    application.add_middleware(
        APIKeyMiddleware,
        api_key=settings.api_key if settings else None,
    )

    # 3. Body size guard for audio upload endpoints
    application.add_middleware(
        MaxBodySizeMiddleware,
        max_bytes=settings.audio_max_upload_bytes if settings else 20_000_000,
    )

    # 4. CORS — configured from environment
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins_list if settings else [],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    return application


app = create_app()


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


@app.post("/v1/transcribe")
async def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
    """
    Convenience endpoint: transcribe an audio file.

    Accepts a multipart audio upload, optionally preprocesses it with ffmpeg,
    constructs an OpenAI chat payload with the configured system prompt,
    forwards through the standard pipeline, and returns the transcript.
    """
    settings = get_settings()

    try:
        # Read uploaded audio bytes
        file_bytes = await file.read()

        # Preprocess audio (normalizes to WAV if enabled, enforces size limit)
        try:
            audio_bytes = await normalize_audio_to_wav(file_bytes, settings)
        except AudioPreprocessError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"type": e.error_type, "message": e.message}},
            )

        # Base64-encode audio for OpenAI payload
        b64_audio = base64.b64encode(audio_bytes).decode("ascii")

        # Build OpenAI chat completion request
        request_body: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": settings.transcribe_system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": b64_audio, "format": "wav"},
                        }
                    ],
                },
            ],
        }

        # Select upstream and forward
        try:
            base_url = select_upstream_url(request_body, settings)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail={"error": {"type": "configuration_error", "message": str(e)}},
            )

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

        # Parse upstream response to extract transcript
        try:
            resp_json = upstream_response.json()
            transcript = resp_json["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": {
                        "type": "upstream_invalid_response",
                        "message": "Upstream returned an unexpected response structure",
                    }
                },
            )

        return TranscribeResponse(transcript=transcript)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in transcribe: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"type": "internal_error", "message": "An unexpected error occurred"}},
        )


@app.post("/v1/analyze")
async def analyze(
    file: UploadFile = File(...),
    instruction: str = Form(...),
) -> AnalyzeResponse:
    """
    Convenience endpoint: analyze an audio file with a custom instruction.

    Accepts a multipart audio upload and an instruction string, optionally
    preprocesses the audio with ffmpeg, constructs an OpenAI chat payload
    with the instruction as system prompt, forwards through the standard
    pipeline, and returns the analysis result.
    """
    settings = get_settings()

    try:
        # Read uploaded audio bytes
        file_bytes = await file.read()

        # Preprocess audio (normalizes to WAV if enabled, enforces size limit)
        try:
            audio_bytes = await normalize_audio_to_wav(file_bytes, settings)
        except AudioPreprocessError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"type": e.error_type, "message": e.message}},
            )

        # Base64-encode audio for OpenAI payload
        b64_audio = base64.b64encode(audio_bytes).decode("ascii")

        # Compose system prompt: optional prefix + instruction
        if settings.analyze_system_prompt_prefix:
            system_prompt = f"{settings.analyze_system_prompt_prefix}\n{instruction}"
        else:
            system_prompt = instruction

        # Build OpenAI chat completion request
        request_body: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": b64_audio, "format": "wav"},
                        }
                    ],
                },
            ],
        }

        # Select upstream and forward
        try:
            base_url = select_upstream_url(request_body, settings)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail={"error": {"type": "configuration_error", "message": str(e)}},
            )

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

        # Parse upstream response to extract result
        try:
            resp_json = upstream_response.json()
            result = resp_json["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": {
                        "type": "upstream_invalid_response",
                        "message": "Upstream returned an unexpected response structure",
                    }
                },
            )

        return AnalyzeResponse(result=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in analyze: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"type": "internal_error", "message": "An unexpected error occurred"}},
        )
