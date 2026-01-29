"""High-level operations API for the inference gateway library."""

import base64
import json
import logging
from typing import Any

from inference_gateway.core.audio import normalize_audio_to_wav
from inference_gateway.core.client import forward_chat_completion, forward_models
from inference_gateway.core.config import GatewayConfig
from inference_gateway.core.exceptions import InvalidRequestError
from inference_gateway.core.routing import select_upstream_url

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_bytes: bytes,
    config: GatewayConfig,
    system_prompt: str | None = None,
) -> str:
    """Transcribe audio and return text transcript."""
    processed_audio = await normalize_audio_to_wav(audio_bytes, config)
    b64_audio = base64.b64encode(processed_audio).decode("ascii")
    prompt = system_prompt if system_prompt is not None else config.transcribe_system_prompt
    
    request_body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": prompt},
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
    
    base_url = select_upstream_url(request_body, config)
    upstream_response = await forward_chat_completion(request_body, base_url, config)
    
    try:
        resp_json = upstream_response.json()
        transcript = resp_json["choices"][0]["message"]["content"]
        return transcript
    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse upstream response: {e}")
        raise InvalidRequestError("Upstream returned an unexpected response structure") from e


async def analyze_audio(
    audio_bytes: bytes,
    instruction: str,
    config: GatewayConfig,
    system_prompt_prefix: str | None = None,
) -> str:
    """Analyze audio with a custom instruction and return the analysis result."""
    processed_audio = await normalize_audio_to_wav(audio_bytes, config)
    b64_audio = base64.b64encode(processed_audio).decode("ascii")
    
    prefix = system_prompt_prefix if system_prompt_prefix is not None else config.analyze_system_prompt_prefix
    if prefix:
        system_prompt = f"{prefix}\n{instruction}"
    else:
        system_prompt = instruction
    
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
    
    base_url = select_upstream_url(request_body, config)
    upstream_response = await forward_chat_completion(request_body, base_url, config)
    
    try:
        resp_json = upstream_response.json()
        result = resp_json["choices"][0]["message"]["content"]
        return result
    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse upstream response: {e}")
        raise InvalidRequestError("Upstream returned an unexpected response structure") from e


async def chat_completion(
    messages: list[dict[str, Any]],
    config: GatewayConfig,
    **openai_params,
) -> dict[str, Any]:
    """Send a chat completion request and return the response."""
    request_body: dict[str, Any] = {
        "messages": messages,
        **openai_params,
    }
    
    base_url = select_upstream_url(request_body, config)
    upstream_response = await forward_chat_completion(request_body, base_url, config)
    
    try:
        return upstream_response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse upstream response: {e}")
        raise InvalidRequestError("Upstream returned invalid JSON") from e


async def list_models(config: GatewayConfig) -> dict[str, Any]:
    """List available models from upstream backend."""
    from inference_gateway.core.exceptions import ConfigurationError
    
    if config.routing_mode == "single":
        base_url = config.effective_base_url
        if not base_url:
            raise ConfigurationError("No upstream URL configured. Please set text_base_url in your GatewayConfig.")
    elif config.routing_mode == "audio_text":
        base_url = config.text_base_url
        if not base_url:
            raise ConfigurationError("text_base_url is required for list_models operation.")
    else:
        raise ConfigurationError(f"Unknown routing mode: {config.routing_mode}")
    
    upstream_response = await forward_models(base_url, config)
    
    try:
        return upstream_response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse upstream response: {e}")
        raise InvalidRequestError("Upstream returned invalid JSON") from e
