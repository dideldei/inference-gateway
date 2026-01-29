"""Backend routing logic - selects upstream based on request structure."""

from inference_gateway.core.config import GatewayConfig
from inference_gateway.core.exceptions import ConfigurationError


def has_audio_content(messages: list) -> bool:
    """
    Detect if messages contain audio content parts.
    
    Checks if any message has content that is a list containing parts
    with type "input_audio" or "audio".
    
    Args:
        messages: List of message dicts from OpenAI chat completion request
        
    Returns:
        True if audio content is detected, False otherwise
    """
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("input_audio", "audio"):
                    return True
    return False


def select_upstream_url(request_body: dict, config: GatewayConfig) -> str:
    """
    Select the upstream base URL based on routing mode and request structure.
    
    Args:
        request_body: The request body dict (for chat completions)
        config: Gateway configuration
        
    Returns:
        Base URL string for the selected upstream
        
    Raises:
        ConfigurationError: If required upstream URL is missing
    """
    if config.routing_mode == "single":
        base_url = config.effective_base_url
        if not base_url:
            raise ConfigurationError(
                "No upstream URL configured for single routing mode. "
                "Please set text_base_url in your GatewayConfig."
            )
        return base_url
    
    elif config.routing_mode == "audio_text":
        # Check if request contains audio content
        messages = request_body.get("messages", [])
        if has_audio_content(messages):
            if not config.audio_base_url:
                raise ConfigurationError(
                    "audio_base_url is required when routing audio requests. "
                    "Please set audio_base_url in your GatewayConfig."
                )
            return config.audio_base_url
        else:
            if not config.text_base_url:
                raise ConfigurationError(
                    "text_base_url is required when routing text requests. "
                    "Please set text_base_url in your GatewayConfig."
                )
            return config.text_base_url
    
    else:
        raise ConfigurationError(f"Unknown routing mode: {config.routing_mode}")
