"""Tests for /v1/analyze convenience endpoint."""

import io
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
    """Settings with analyze_system_prompt_prefix set."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="audio_text",
        analyze_system_prompt_prefix="You are an audio analyst.",
        audio_preprocess_enabled="1",
        audio_max_upload_bytes=1_000_000,
    )


@pytest.fixture
def mock_settings_no_prefix():
    """Settings with empty analyze_system_prompt_prefix."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="audio_text",
        analyze_system_prompt_prefix="",
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


def _upload(data: bytes = b"fake audio", filename: str = "test.wav", instruction: str = "Summarize this audio"):
    """Helper to build multipart form data for TestClient."""
    return {
        "files": {"file": (filename, io.BytesIO(data), "audio/wav")},
        "data": {"instruction": instruction},
    }


def _mock_upstream_response(result: str) -> httpx.Response:
    """Build a mock upstream response with the given result."""
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": result}}]},
    )


# --- Happy path ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_success(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Successful analysis returns JSON with result field."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"normalized wav bytes"
    mock_forward.return_value = _mock_upstream_response("The audio contains a conversation about weather.")

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "The audio contains a conversation about weather."


# --- Payload construction with prefix ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_payload_with_prefix(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """System prompt = prefix + newline + instruction when prefix is set."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = _mock_upstream_response("result")

    client.post("/v1/analyze", **_upload(instruction="Detect the language"))

    mock_forward.assert_called_once()
    request_body = mock_forward.call_args[0][0]

    assert request_body["messages"][0]["role"] == "system"
    assert request_body["messages"][0]["content"] == "You are an audio analyst.\nDetect the language"

    # User message contains input_audio part
    user_content = request_body["messages"][1]["content"]
    assert isinstance(user_content, list)
    assert user_content[0]["type"] == "input_audio"
    assert user_content[0]["input_audio"]["format"] == "wav"


# --- Payload construction without prefix ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_payload_no_prefix(mock_normalize, mock_forward, mock_get_settings, mock_settings_no_prefix):
    """System prompt = just instruction when prefix is empty."""
    mock_get_settings.return_value = mock_settings_no_prefix
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = _mock_upstream_response("result")

    client.post("/v1/analyze", **_upload(instruction="Count the speakers"))

    request_body = mock_forward.call_args[0][0]
    assert request_body["messages"][0]["content"] == "Count the speakers"


# --- Instruction passed verbatim ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_instruction_verbatim(mock_normalize, mock_forward, mock_get_settings, mock_settings_no_prefix):
    """Instruction is passed verbatim without modification."""
    mock_get_settings.return_value = mock_settings_no_prefix
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = _mock_upstream_response("ok")

    instruction = "  Extract keywords & summarize.  \n\nInclude timestamps.  "
    client.post("/v1/analyze", **_upload(instruction=instruction))

    request_body = mock_forward.call_args[0][0]
    assert request_body["messages"][0]["content"] == instruction


# --- Audio preprocessing error ---


@patch("app.main.get_settings")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_audio_too_large(mock_normalize, mock_get_settings, mock_settings):
    """Oversized audio returns 400."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.side_effect = AudioPreprocessError(
        "Audio upload exceeds maximum size", error_type="audio_too_large"
    )

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["type"] == "audio_too_large"


# --- Upstream errors ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_upstream_unreachable(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream connection failure returns 502."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.side_effect = UpstreamUnreachableError("Connection failed", "http://127.0.0.1:8080")

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 502
    assert response.json()["detail"]["error"]["type"] == "upstream_unreachable"


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_upstream_timeout(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream timeout returns 504."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.side_effect = UpstreamTimeoutError("Timeout", "http://127.0.0.1:8080")

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 504
    assert response.json()["detail"]["error"]["type"] == "upstream_timeout"


# --- Invalid upstream response ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_upstream_invalid_response(mock_normalize, mock_forward, mock_get_settings, mock_settings):
    """Upstream returning unexpected JSON structure returns 502."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = httpx.Response(200, json={"unexpected": "shape"})

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 502
    assert response.json()["detail"]["error"]["type"] == "upstream_invalid_response"


# --- Preprocessing disabled ---


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_analyze_preprocessing_disabled(mock_normalize, mock_forward, mock_get_settings, mock_settings_preprocess_disabled):
    """Endpoint works when audio preprocessing is disabled."""
    mock_get_settings.return_value = mock_settings_preprocess_disabled
    mock_normalize.return_value = b"raw audio"
    mock_forward.return_value = _mock_upstream_response("analysis result")

    response = client.post("/v1/analyze", **_upload())

    assert response.status_code == 200
    assert response.json()["result"] == "analysis result"
    mock_normalize.assert_called_once()
