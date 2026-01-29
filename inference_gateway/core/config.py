"""Simple configuration for core library usage."""

from dataclasses import dataclass


@dataclass
class GatewayConfig:
    """Configuration for inference gateway core library.

    This is a simplified config suitable for library usage without
    environment variable loading.

    Args:
        text_base_url: Base URL for text-only inference backend
        audio_base_url: Optional base URL for audio-capable inference backend
        routing_mode: Routing strategy - "single" or "audio_text"
        timeout_s: Total timeout for upstream requests in seconds
        connect_timeout_s: Connection timeout for upstream requests in seconds
        audio_preprocess_enabled: Enable audio preprocessing with ffmpeg
        audio_max_upload_bytes: Maximum audio upload size in bytes
        audio_target_sr: Target sample rate for audio normalization (Hz)
        audio_target_channels: Target number of audio channels (1=mono, 2=stereo)
        audio_loudnorm: Enable EBU R128 loudness normalization
        audio_loudnorm_filter: ffmpeg loudness normalization filter parameters
        ffmpeg_bin: Path to ffmpeg binary
        transcribe_system_prompt: System prompt for transcription operations
        analyze_system_prompt_prefix: Prefix for analyze operation system prompts
    """

    text_base_url: str
    audio_base_url: str | None = None
    routing_mode: str = "single"
    timeout_s: float = 300.0
    connect_timeout_s: float = 10.0

    # Audio preprocessing settings
    audio_preprocess_enabled: bool = False
    audio_max_upload_bytes: int = 20_000_000
    audio_target_sr: int = 16000
    audio_target_channels: int = 1
    audio_loudnorm: bool = True
    audio_loudnorm_filter: str = "loudnorm=I=-16:TP=-1.5:LRA=11"
    ffmpeg_bin: str = "ffmpeg"

    # Prompt settings
    transcribe_system_prompt: str = (
        "You are a helpful assistant that transcribes audio. "
        "Listen carefully and provide an accurate transcription."
    )
    analyze_system_prompt_prefix: str = ""

    @property
    def effective_base_url(self) -> str | None:
        """Return the effective base URL for single routing mode."""
        return self.text_base_url

    @property
    def audio_preprocess_enabled_bool(self) -> bool:
        """Backward compatibility property."""
        return self.audio_preprocess_enabled

    @property
    def audio_loudnorm_bool(self) -> bool:
        """Backward compatibility property."""
        return self.audio_loudnorm
