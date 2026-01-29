"""Tests for request forwarding."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.forwarder import UpstreamTimeoutError, UpstreamUnreachableError, forward_chat_completion, forward_models
from app.main import app
from app.routing import has_audio_content, select_upstream_url

client = TestClient(app)


@pytest.fixture
def mock_settings():
    """Create a mock settings object for testing."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        default_base_url=None,
        routing_mode="single",
        upstream_timeout_s=300.0,
        upstream_connect_timeout_s=10.0,
    )


@pytest.fixture
def mock_settings_audio_text():
    """Create a mock settings object for audio_text routing mode."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        default_base_url=None,
        routing_mode="audio_text",
        upstream_timeout_s=300.0,
        upstream_connect_timeout_s=10.0,
    )


@pytest.mark.asyncio
async def test_forward_chat_completion_success(mock_settings):
    """Test successful forwarding of chat completion request."""
    mock_response = httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "Hello"}}]},
    )
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        response = await forward_chat_completion(
            {"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
            "http://127.0.0.1:11434",
            mock_settings,
        )
        
        assert response.status_code == 200
        assert response.json() == {"choices": [{"message": {"role": "assistant", "content": "Hello"}}]}


@pytest.mark.asyncio
async def test_forward_chat_completion_connection_error(mock_settings):
    """Test handling of connection errors."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("Connection failed")):
        with pytest.raises(UpstreamUnreachableError) as exc_info:
            await forward_chat_completion(
                {"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
                "http://127.0.0.1:11434",
                mock_settings,
            )
        
        assert "Connection to upstream failed" in str(exc_info.value.message)
        assert exc_info.value.upstream == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_forward_chat_completion_timeout(mock_settings):
    """Test handling of timeout errors."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(UpstreamTimeoutError) as exc_info:
            await forward_chat_completion(
                {"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
                "http://127.0.0.1:11434",
                mock_settings,
            )
        
        assert "did not respond in time" in str(exc_info.value.message)
        assert exc_info.value.upstream == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_forward_models_success(mock_settings):
    """Test successful forwarding of models request."""
    mock_response = httpx.Response(
        200,
        json={"data": [{"id": "model1"}, {"id": "model2"}]},
    )
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        response = await forward_models("http://127.0.0.1:11434", mock_settings)
        
        assert response.status_code == 200
        assert response.json() == {"data": [{"id": "model1"}, {"id": "model2"}]}


@pytest.mark.asyncio
async def test_forward_models_connection_error(mock_settings):
    """Test handling of connection errors in models endpoint."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.ConnectError("Connection failed")):
        with pytest.raises(UpstreamUnreachableError):
            await forward_models("http://127.0.0.1:11434", mock_settings)


def test_has_audio_content_detects_audio():
    """Test audio content detection in messages."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": {"data": "base64..."}},
            ],
        }
    ]
    assert has_audio_content(messages) is True


def test_has_audio_content_detects_audio_type_variant():
    """Test audio content detection with 'audio' type."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "audio", "audio": {"data": "base64..."}},
            ],
        }
    ]
    assert has_audio_content(messages) is True


def test_has_audio_content_no_audio():
    """Test that text-only messages don't trigger audio detection."""
    messages = [
        {"role": "user", "content": "Hello, world!"},
    ]
    assert has_audio_content(messages) is False


def test_has_audio_content_mixed():
    """Test that mixed content (text + audio) is detected."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Transcribe this"},
                {"type": "input_audio", "input_audio": {"data": "base64..."}},
            ],
        }
    ]
    assert has_audio_content(messages) is True


def test_select_upstream_url_single_mode(mock_settings):
    """Test upstream URL selection in single routing mode."""
    request_body = {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    url = select_upstream_url(request_body, mock_settings)
    assert url == "http://127.0.0.1:11434"


def test_select_upstream_url_audio_text_mode_text(mock_settings_audio_text):
    """Test upstream URL selection for text requests in audio_text mode."""
    request_body = {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    url = select_upstream_url(request_body, mock_settings_audio_text)
    assert url == "http://127.0.0.1:11434"  # TEXT_BASE_URL


def test_select_upstream_url_audio_text_mode_audio(mock_settings_audio_text):
    """Test upstream URL selection for audio requests in audio_text mode."""
    request_body = {
        "model": "test",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": "base64..."}},
                ],
            }
        ],
    }
    url = select_upstream_url(request_body, mock_settings_audio_text)
    assert url == "http://127.0.0.1:8080"  # AUDIO_BASE_URL


def test_select_upstream_url_missing_url():
    """Test that missing upstream URL raises ValueError."""
    settings = Settings(
        text_base_url=None,
        audio_base_url=None,
        default_base_url=None,
        routing_mode="single",
        upstream_timeout_s=300.0,
        upstream_connect_timeout_s=10.0,
    )
    request_body = {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    
    with pytest.raises(ValueError, match="No upstream URL configured"):
        select_upstream_url(request_body, settings)


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
def test_chat_completions_endpoint_success(mock_forward, mock_get_settings, mock_settings):
    """Test successful chat completions endpoint."""
    mock_get_settings.return_value = mock_settings
    mock_response = httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "Hello"}}]},
    )
    mock_forward.return_value = mock_response
    
    response = client.post(
        "/v1/chat/completions",
        json={"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
    )
    
    assert response.status_code == 200
    assert response.json() == {"choices": [{"message": {"role": "assistant", "content": "Hello"}}]}


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
def test_chat_completions_endpoint_502(mock_forward, mock_get_settings, mock_settings):
    """Test chat completions endpoint returns 502 on upstream unreachable."""
    mock_get_settings.return_value = mock_settings
    mock_forward.side_effect = UpstreamUnreachableError("Connection failed", "http://127.0.0.1:11434")
    
    response = client.post(
        "/v1/chat/completions",
        json={"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
    )
    
    assert response.status_code == 502
    data = response.json()
    assert data["error"]["type"] == "upstream_unreachable"
    assert data["upstream"] == "http://127.0.0.1:11434"


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
def test_chat_completions_endpoint_504(mock_forward, mock_get_settings, mock_settings):
    """Test chat completions endpoint returns 504 on upstream timeout."""
    mock_get_settings.return_value = mock_settings
    mock_forward.side_effect = UpstreamTimeoutError("Timeout", "http://127.0.0.1:11434")
    
    response = client.post(
        "/v1/chat/completions",
        json={"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
    )
    
    assert response.status_code == 504
    data = response.json()
    assert data["error"]["type"] == "upstream_timeout"
    assert data["upstream"] == "http://127.0.0.1:11434"


@patch("app.main.get_settings")
def test_chat_completions_endpoint_invalid_json(mock_get_settings, mock_settings):
    """Test chat completions endpoint returns 400 on invalid JSON."""
    mock_get_settings.return_value = mock_settings
    
    response = client.post(
        "/v1/chat/completions",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["type"] == "invalid_json"


@patch("app.main.get_settings")
def test_chat_completions_endpoint_not_dict(mock_get_settings, mock_settings):
    """Test chat completions endpoint returns 400 when body is not a dict."""
    mock_get_settings.return_value = mock_settings
    
    response = client.post(
        "/v1/chat/completions",
        json=["not", "a", "dict"],
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["type"] == "invalid_request"


@patch("app.main.get_settings")
@patch("app.main.forward_models")
def test_models_endpoint_success(mock_forward, mock_get_settings, mock_settings):
    """Test successful models endpoint."""
    mock_get_settings.return_value = mock_settings
    mock_response = httpx.Response(
        200,
        json={"data": [{"id": "model1"}, {"id": "model2"}]},
    )
    mock_forward.return_value = mock_response
    
    response = client.get("/v1/models")
    
    assert response.status_code == 200
    assert response.json() == {"data": [{"id": "model1"}, {"id": "model2"}]}


@patch("app.main.get_settings")
@patch("app.main.forward_models")
def test_models_endpoint_502(mock_forward, mock_get_settings, mock_settings):
    """Test models endpoint returns 502 on upstream unreachable."""
    mock_get_settings.return_value = mock_settings
    mock_forward.side_effect = UpstreamUnreachableError("Connection failed", "http://127.0.0.1:11434")
    
    response = client.get("/v1/models")
    
    assert response.status_code == 502
    data = response.json()
    assert data["error"]["type"] == "upstream_unreachable"


@patch("app.main.get_settings")
@patch("app.main.forward_models")
def test_models_endpoint_504(mock_forward, mock_get_settings, mock_settings):
    """Test models endpoint returns 504 on upstream timeout."""
    mock_get_settings.return_value = mock_settings
    mock_forward.side_effect = UpstreamTimeoutError("Timeout", "http://127.0.0.1:11434")
    
    response = client.get("/v1/models")
    
    assert response.status_code == 504
    data = response.json()
    assert data["error"]["type"] == "upstream_timeout"


@patch("app.main.get_settings")
def test_models_endpoint_audio_text_mode(mock_get_settings, mock_settings_audio_text):
    """Test models endpoint uses TEXT upstream in audio_text mode."""
    mock_get_settings.return_value = mock_settings_audio_text
    
    with patch("app.main.forward_models") as mock_forward:
        mock_response = httpx.Response(200, json={"data": []})
        mock_forward.return_value = mock_response
        
        client.get("/v1/models")
        
        # Should call forward_models with TEXT_BASE_URL
        mock_forward.assert_called_once()
        call_args = mock_forward.call_args
        assert call_args[0][0] == "http://127.0.0.1:11434"  # TEXT_BASE_URL


@patch("app.main.get_settings")
@patch("app.main.forward_chat_completion")
def test_chat_completions_non_json_response(mock_forward, mock_get_settings, mock_settings):
    """Test that non-JSON upstream responses are passed through."""
    mock_get_settings.return_value = mock_settings
    mock_response = httpx.Response(
        200,
        content=b"plain text response",
        headers={"content-type": "text/plain"},
    )
    mock_forward.return_value = mock_response
    
    response = client.post(
        "/v1/chat/completions",
        json={"model": "test", "messages": [{"role": "user", "content": "Hi"}]},
    )
    
    assert response.status_code == 200
    # Response should be passed through as-is (though FastAPI TestClient may parse it)
    assert response.headers["content-type"] == "text/plain"
