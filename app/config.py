"""Configuration management - loads environment variables into typed settings."""

import logging
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gateway Server Configuration
    gateway_host: str = Field(default="127.0.0.1", description="Host for the gateway to listen on")
    gateway_port: int = Field(default=8090, description="Port for the gateway to listen on")

    # Upstream Backend URLs
    text_base_url: str | None = Field(
        default=None,
        description="Base URL for text-only inference requests (e.g., http://127.0.0.1:11434)",
    )
    audio_base_url: str | None = Field(
        default=None,
        description="Base URL for audio-enabled inference requests (e.g., http://127.0.0.1:8080)",
    )
    default_base_url: str | None = Field(
        default=None,
        description="Default upstream URL (optional; if empty, uses TEXT_BASE_URL). Used when ROUTING_MODE=single",
    )

    # Routing Configuration
    routing_mode: Literal["single", "audio_text"] = Field(
        default="single",
        description="Routing mode: 'single' (one upstream) or 'audio_text' (route by content type)",
    )

    # Timeout Configuration
    upstream_timeout_s: float = Field(
        default=300.0,
        description="Total timeout for upstream requests (seconds)",
    )
    upstream_connect_timeout_s: float = Field(
        default=10.0,
        description="Connection timeout for upstream requests (seconds)",
    )

    # Security Configuration
    api_key: str | None = Field(
        default=None,
        description="API key for gateway authentication (optional). If set, requires Authorization: Bearer <API_KEY>",
    )
    allow_origins: str = Field(
        default="",
        description="CORS allowed origins (comma-separated list, empty = no CORS)",
    )

    # Audio Preprocessing Configuration
    ffmpeg_bin: str = Field(
        default="ffmpeg",
        description="Path to ffmpeg binary (default: 'ffmpeg' - must be in PATH)",
    )
    audio_preprocess_enabled: str = Field(
        default="1",
        description="Enable audio preprocessing (1 = enabled, 0 = disabled)",
    )
    audio_target_sr: int = Field(
        default=16000,
        description="Target sample rate for audio normalization (Hz)",
    )
    audio_target_channels: int = Field(
        default=1,
        description="Target number of audio channels (1 = mono, 2 = stereo)",
    )
    audio_loudnorm: str = Field(
        default="1",
        description="Enable loudness normalization (1 = enabled, 0 = disabled)",
    )
    audio_loudnorm_filter: str = Field(
        default="loudnorm=I=-16:TP=-1.5:LRA=11",
        description="Loudness normalization filter parameters (EBU R128)",
    )

    # Convenience Endpoint Prompts
    transcribe_system_prompt: str = Field(
        default="You are a helpful assistant that transcribes audio accurately.",
        description="System prompt for /v1/transcribe endpoint",
    )
    analyze_system_prompt_prefix: str = Field(
        default="",
        description="Optional prefix for /v1/analyze endpoint system prompt",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    log_request_bodies: str = Field(
        default="0",
        description="Log request bodies (1 = enabled, 0 = disabled). WARNING: Only enable in development",
    )

    @field_validator("gateway_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"gateway_port must be between 1 and 65535, got {v}")
        return v

    @field_validator("upstream_timeout_s", "upstream_connect_timeout_s")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError(f"Timeout must be positive, got {v}")
        return v

    @field_validator("text_base_url", "audio_base_url", "default_base_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate URL format if provided."""
        if v is None or v == "":
            return None
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL must use http or https scheme, got {v}")
        if not parsed.netloc:
            raise ValueError(f"URL must have a valid host, got {v}")
        return v

    @field_validator("routing_mode")
    @classmethod
    def validate_routing_mode(cls, v: str) -> str:
        """Validate routing mode is valid."""
        if v not in ("single", "audio_text"):
            raise ValueError(f"routing_mode must be 'single' or 'audio_text', got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got {v}")
        return v.upper()

    @field_validator("audio_preprocess_enabled", "audio_loudnorm", "log_request_bodies")
    @classmethod
    def validate_boolean_string(cls, v: str) -> str:
        """Validate boolean string format."""
        v_lower = v.lower().strip()
        if v_lower not in ("0", "1", "true", "false", "yes", "no"):
            raise ValueError(f"Boolean field must be '0', '1', 'true', 'false', 'yes', or 'no', got {v}")
        return v

    @model_validator(mode="after")
    def validate_routing_dependencies(self) -> "Settings":
        """Validate that required upstream URLs are set based on routing mode."""
        if self.routing_mode == "audio_text":
            if not self.text_base_url:
                raise ValueError(
                    "TEXT_BASE_URL is required when ROUTING_MODE=audio_text. "
                    "Please set TEXT_BASE_URL in your .env file."
                )
            if not self.audio_base_url:
                raise ValueError(
                    "AUDIO_BASE_URL is required when ROUTING_MODE=audio_text. "
                    "Please set AUDIO_BASE_URL in your .env file."
                )
        elif self.routing_mode == "single":
            if not self.default_base_url and not self.text_base_url:
                raise ValueError(
                    "Either DEFAULT_BASE_URL or TEXT_BASE_URL must be set when ROUTING_MODE=single. "
                    "Please set at least one of these in your .env file."
                )
        return self

    @property
    def allow_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if not self.allow_origins:
            return []
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]

    @property
    def audio_preprocess_enabled_bool(self) -> bool:
        """Convert audio_preprocess_enabled string to boolean."""
        v = self.audio_preprocess_enabled.lower().strip()
        return v in ("1", "true", "yes")

    @property
    def audio_loudnorm_bool(self) -> bool:
        """Convert audio_loudnorm string to boolean."""
        v = self.audio_loudnorm.lower().strip()
        return v in ("1", "true", "yes")

    @property
    def log_request_bodies_bool(self) -> bool:
        """Convert log_request_bodies string to boolean."""
        v = self.log_request_bodies.lower().strip()
        return v in ("1", "true", "yes")

    @property
    def effective_base_url(self) -> str:
        """Get the effective base URL for single routing mode."""
        if self.routing_mode == "single":
            return self.default_base_url or self.text_base_url or ""
        return self.text_base_url or ""

    def get_log_level(self) -> int:
        """Convert log level string to logging constant."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(self.log_level, logging.INFO)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the application settings singleton.

    Settings are loaded from environment variables and .env file on first call.
    Subsequent calls return the cached instance.

    Raises:
        ValueError: If required settings are missing or invalid.

    Returns:
        Settings: The validated settings instance.
    """
    try:
        return Settings()
    except Exception as e:
        raise ValueError(
            f"Failed to load configuration: {e}\n"
            "Please check your .env file and ensure all required settings are present and valid."
        ) from e
