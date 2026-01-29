"""Backend routing logic - selects upstream based on request structure."""

from app.config import Settings


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


def select_upstream_url(request_body: dict, settings: Settings) -> str:
    """
    Select the upstream base URL based on routing mode and request structure.
    
    Args:
        request_body: The request body dict (for chat completions)
        settings: Application settings
        
    Returns:
        Base URL string for the selected upstream
        
    Raises:
        ValueError: If required upstream URL is missing
    """
    if settings.routing_mode == "single":
        base_url = settings.effective_base_url
        if not base_url:
            raise ValueError(
                "No upstream URL configured for single routing mode. "
                "Please set DEFAULT_BASE_URL or TEXT_BASE_URL in your .env file."
            )
        return base_url
    
    elif settings.routing_mode == "audio_text":
        # Check if request contains audio content
        messages = request_body.get("messages", [])
        if has_audio_content(messages):
            if not settings.audio_base_url:
                raise ValueError(
                    "AUDIO_BASE_URL is required when routing audio requests. "
                    "Please set AUDIO_BASE_URL in your .env file."
                )
            return settings.audio_base_url
        else:
            if not settings.text_base_url:
                raise ValueError(
                    "TEXT_BASE_URL is required when routing text requests. "
                    "Please set TEXT_BASE_URL in your .env file."
                )
            return settings.text_base_url
    
    else:
        raise ValueError(f"Unknown routing mode: {settings.routing_mode}")
