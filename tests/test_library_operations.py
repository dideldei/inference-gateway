"""Tests for the library operations module."""

import base64
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from inference_gateway import (
    GatewayConfig,
    analyze_audio,
    chat_completion,
    list_models,
    transcribe_audio,
)
from inference_gateway.core.exceptions import InvalidRequestError, UpstreamUnreachableError


@pytest.fixture
def config():
    """Create a test configuration."""
    return GatewayConfig(
        text_base_url="http://test-text:8080",
        audio_base_url="http://test-audio:8080",
        routing_mode="audio_text",
        audio_preprocess_enabled=False,  # Disable preprocessing for simpler tests
    )


@pytest.fixture
def mock_response():
    """Create a mock httpx.Response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test transcript"
                },
                "finish_reason": "stop"
            }
        ]
    }
    return response


@pytest.mark.asyncio
async def test_transcribe_audio_basic(config, mock_response):
    """Test basic audio transcription."""
    audio_bytes = b"fake audio data"

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        transcript = await transcribe_audio(audio_bytes, config)

        assert transcript == "Test transcript"
        mock_forward.assert_called_once()

        # Verify the request body structure
        call_args = mock_forward.call_args
        request_body = call_args[0][0]
        assert "messages" in request_body
        assert len(request_body["messages"]) == 2
        assert request_body["messages"][0]["role"] == "system"
        assert request_body["messages"][1]["role"] == "user"

        # Verify audio content
        user_content = request_body["messages"][1]["content"]
        assert isinstance(user_content, list)
        assert user_content[0]["type"] == "input_audio"
        assert "data" in user_content[0]["input_audio"]


@pytest.mark.asyncio
async def test_transcribe_audio_custom_prompt(config, mock_response):
    """Test transcription with custom system prompt."""
    audio_bytes = b"fake audio data"
    custom_prompt = "Custom transcription instructions"

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        await transcribe_audio(audio_bytes, config, system_prompt=custom_prompt)

        call_args = mock_forward.call_args
        request_body = call_args[0][0]
        assert request_body["messages"][0]["content"] == custom_prompt


@pytest.mark.asyncio
async def test_analyze_audio_basic(config, mock_response):
    """Test basic audio analysis."""
    audio_bytes = b"fake audio data"
    instruction = "Summarize the key points"

    mock_response.json.return_value["choices"][0]["message"]["content"] = "Summary result"

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        result = await analyze_audio(audio_bytes, instruction, config)

        assert result == "Summary result"

        call_args = mock_forward.call_args
        request_body = call_args[0][0]
        assert request_body["messages"][0]["content"] == instruction


@pytest.mark.asyncio
async def test_analyze_audio_with_prefix(config, mock_response):
    """Test audio analysis with system prompt prefix."""
    audio_bytes = b"fake audio data"
    instruction = "Summarize the key points"
    prefix = "You are an expert analyst."

    mock_response.json.return_value["choices"][0]["message"]["content"] = "Summary result"

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        await analyze_audio(audio_bytes, instruction, config, system_prompt_prefix=prefix)

        call_args = mock_forward.call_args
        request_body = call_args[0][0]
        assert request_body["messages"][0]["content"] == f"{prefix}\n{instruction}"


@pytest.mark.asyncio
async def test_chat_completion_basic(config, mock_response):
    """Test basic chat completion."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        response = await chat_completion(messages, config)

        assert response["id"] == "chatcmpl-123"
        assert response["choices"][0]["message"]["content"] == "Test transcript"


@pytest.mark.asyncio
async def test_chat_completion_with_params(config, mock_response):
    """Test chat completion with additional OpenAI parameters."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        await chat_completion(
            messages,
            config,
            temperature=0.7,
            max_tokens=100,
            model="gpt-4"
        )

        call_args = mock_forward.call_args
        request_body = call_args[0][0]
        assert request_body["temperature"] == 0.7
        assert request_body["max_tokens"] == 100
        assert request_body["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_list_models_single_mode(mock_response):
    """Test listing models in single routing mode."""
    config = GatewayConfig(
        text_base_url="http://test:8080",
        routing_mode="single"
    )

    mock_response.json.return_value = {
        "object": "list",
        "data": [{"id": "model-1", "object": "model"}]
    }

    with patch("inference_gateway.core.operations.forward_models", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        result = await list_models(config)

        assert result["object"] == "list"
        assert len(result["data"]) == 1
        mock_forward.assert_called_once_with("http://test:8080", config)


@pytest.mark.asyncio
async def test_list_models_audio_text_mode(config, mock_response):
    """Test listing models in audio_text routing mode (uses text upstream)."""
    mock_response.json.return_value = {
        "object": "list",
        "data": [{"id": "model-1", "object": "model"}]
    }

    with patch("inference_gateway.core.operations.forward_models", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        await list_models(config)

        # Should use text_base_url, not audio_base_url
        mock_forward.assert_called_once_with("http://test-text:8080", config)


@pytest.mark.asyncio
async def test_transcribe_invalid_response(config):
    """Test transcription with malformed upstream response."""
    audio_bytes = b"fake audio data"

    mock_response = Mock(spec=httpx.Response)
    mock_response.json.return_value = {"invalid": "structure"}

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = mock_response

        with pytest.raises(InvalidRequestError, match="unexpected response structure"):
            await transcribe_audio(audio_bytes, config)


@pytest.mark.asyncio
async def test_chat_completion_upstream_error(config):
    """Test chat completion with upstream connection error."""
    messages = [{"role": "user", "content": "Hello"}]

    with patch("inference_gateway.core.operations.forward_chat_completion", new_callable=AsyncMock) as mock_forward:
        mock_forward.side_effect = UpstreamUnreachableError(
            "Connection failed",
            upstream="http://test:8080"
        )

        with pytest.raises(UpstreamUnreachableError):
            await chat_completion(messages, config)
