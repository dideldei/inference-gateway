"""Contract tests for /v1/transcribe — verify external API shape with mocked upstream."""

import io
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_settings():
    """Settings for contract tests."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="audio_text",
        transcribe_system_prompt="Transcribe the following audio.",
        audio_preprocess_enabled="1",
        audio_max_upload_bytes=1_000_000,
    )


def _upload(data: bytes = b"fake audio", filename: str = "test.wav"):
    return {"files": {"file": (filename, io.BytesIO(data), "audio/wav")}}


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_contract_returns_transcript_json(
    mock_normalize, mock_forward, mock_get_settings, mock_settings
):
    """Contract: /v1/transcribe returns {"transcript": "<string>"} with 200 and application/json."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"normalized wav"
    mock_forward.return_value = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"role": "assistant", "content": "This is the transcript."}}
            ]
        },
    )

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    # Must have exactly the "transcript" key with a string value
    assert "transcript" in data
    assert isinstance(data["transcript"], str)
    assert data["transcript"] == "This is the transcript."


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
@patch("app.main.normalize_audio_to_wav", new_callable=AsyncMock)
def test_transcribe_contract_error_shape_on_upstream_failure(
    mock_normalize, mock_forward, mock_get_settings, mock_settings
):
    """Contract: upstream failure returns structured error JSON with error.type field."""
    mock_get_settings.return_value = mock_settings
    mock_normalize.return_value = b"wav"
    mock_forward.return_value = httpx.Response(200, json={"unexpected": "shape"})

    response = client.post("/v1/transcribe", **_upload())

    assert response.status_code == 502
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert "type" in data["detail"]["error"]
    assert isinstance(data["detail"]["error"]["type"], str)
