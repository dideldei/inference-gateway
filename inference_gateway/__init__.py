"""Inference Gateway - OpenAI-compatible inference library.

A Python library for interacting with OpenAI-compatible inference backends,
with support for audio preprocessing, intelligent routing, and high-level
operations like transcription and analysis.

Usage:
    >>> from inference_gateway import GatewayConfig, transcribe_audio
    >>>
    >>> config = GatewayConfig(text_base_url="http://localhost:8080")
    >>> audio_bytes = open("recording.mp3", "rb").read()
    >>> transcript = await transcribe_audio(audio_bytes, config)
    >>> print(transcript)
"""

__version__ = "0.2.0"

# Public library API exports
from inference_gateway.core.config import GatewayConfig
from inference_gateway.core.operations import (
    analyze_audio,
    chat_completion,
    list_models,
    transcribe_audio,
)

# Export exceptions for library users
from inference_gateway.core.exceptions import (
    AudioProcessingError,
    ConfigurationError,
    GatewayError,
    InvalidRequestError,
    UpstreamError,
    UpstreamTimeoutError,
    UpstreamUnreachableError,
)

__all__ = [
    "__version__",
    # Configuration
    "GatewayConfig",
    # Operations
    "transcribe_audio",
    "analyze_audio",
    "chat_completion",
    "list_models",
    # Exceptions
    "GatewayError",
    "AudioProcessingError",
    "ConfigurationError",
    "InvalidRequestError",
    "UpstreamError",
    "UpstreamTimeoutError",
    "UpstreamUnreachableError",
]
