"""Tests for /v1/transcribe convenience endpoint."""

import io
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.audio import AudioPreprocessError
from app.config import Settings
from app.forwarder import UpstreamTimeoutError, UpstreamUnreachableError
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_settings():
    """Settings for transcribe tests."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="audio_text",
        transcribe_system_prompt="Transcribe the following audio.",
        audio_preprocess_enabled="1",
        audio_max_upload_bytes=1_000_000,
    )


@pytest.fixture
def mock_settings_preprocess_disabled():
    """Settings with audio preprocessing disabled."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        routing_mode="single",
        audio_preprocess_enabled="0",
        audio_max_upload_bytes=1_000_000,
    )


def _upload(data: bytes = b"fake audio", filename: str = "test.wav"):
    """Helper to build multipart file upload kwargs for TestClient."""
    return {"files": {"file": (filename, io.BytesIO(data), "audio/wav")}}


def _mock_upstream_response(transcript: str) -> httpx.Response:
    """Build a mock upstream response with the given transcript."""
    return httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"role": "assistant", "content": transcript}}
            ]
        },
    )


# --- Happy path ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_success(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Successful transcription returns JSON with transcript field."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"normalized wav bytes"
    mock_forward.return_value = _mock_upstream_response("Hello, world!")

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "Hello, world!"


# --- Payload construction ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_payload_structure(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Verify the constructed OpenAI payload has correct structure."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = _mock_upstream_response("text")

    client.post("/v1/transcribe", **_upload())

    mock_forward.assert_called_once()
    request_body = mock_forward.call_args[0][0]

    # System message uses configured prompt
    assert request_body["messages"][0]["role"] == "system"
    assert request_body["messages"][0]["content"] == "Transcribe the following audio."

    # User message contains input_audio part
    user_content = request_body["messages"][1]["content"]
    assert isinstance(user_content, list)
    assert len(user_content) == 1
    assert user_content[0]["type"] == "input_audio"
    assert user_content[0]["input_audio"]["format"] == "wav"
    assert isinstance(user_content[0]["input_audio"]["data"], str)  # base64 string


# --- Audio preprocessing error ---


@patch("app.main.get_settings")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_audio_too_large(mock_normalize, mock_get_settings, mock_settings):
    """Oversized audio returns 400 with audio_too_large error."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.side_effect = AudioPreprocessError(
        "Audio upload exceeds maximum size", error_type="audio_too_large"
    )

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["type"] == "audio_too_large"


@patch("app.main.get_settings")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_invalid_audio(mock_normalize, mock_get_settings, mock_settings):
    """Invalid audio returns 400 with invalid_audio error."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.side_effect = AudioPreprocessError(
        "ffmpeg failed to decode input audio", error_type="invalid_audio"
    )

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["type"] == "invalid_audio"


# --- Upstream errors ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_upstream_unreachable(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream connection failure returns 502."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.side_effect = UpstreamUnreachableError("Connection failed", "http://127.0.0.1:8080")

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 502
    data = response.json()
    assert data["detail"]["error"]["type"] == "upstream_unreachable"


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_upstream_timeout(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream timeout returns 504."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.side_effect = UpstreamTimeoutError("Timeout", "http://127.0.0.1:8080")

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 504
    data = response.json()
    assert data["detail"]["error"]["type"] == "upstream_timeout"


# --- Invalid upstream response ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_upstream_invalid_response(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream returning unexpected JSON structure returns 502."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = httpx.Response(200, json={"unexpected": "shape"})

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 502
    data = response.json()
    assert data["detail"]["error"]["type"] == "upstream_invalid_response"


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_upstream_empty_choices(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream returning empty choices list returns 502."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = httpx.Response(200, json={"choices": []})

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 502
    data = response.json()
    assert data["detail"]["error"]["type"] == "upstream_invalid_response"


# --- Preprocessing disabled ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_preprocessing_disabled(mock_normalize, mock_forward, mock_get_settings, mock_settings_preprocess_disabled):
    """Endpoint works when audio preprocessing is disabled."""
    mock_get_settings.return_value = mock_settings_preprocess_disabled
    # When disabled, normalize_audio_to_wav returns input unchanged
    mock_normalize.return_value = b"raw audio"
    mock_forward.return_value = _mock_upstream_response("transcribed text")

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 200
    assert response.json()["transcript"] == "transcribed text"
    mock_normalize.assert_called_once()
