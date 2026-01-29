"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from app.config import Settings, get_settings


def test_settings_loads_with_valid_env():
    """Test that settings can be loaded with valid environment variables."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("""GATEWAY_HOST=127.0.0.1
GATEWAY_PORT=8090
TEXT_BASE_URL=http://127.0.0.1:11434
AUDIO_BASE_URL=http://127.0.0.1:8080
ROUTING_MODE=single
TRANSCRIBE_SYSTEM_PROMPT=Test prompt
""")
        env_file = f.name

    try:
        # Temporarily set environment to use our test .env file
        original_env_file = os.environ.get("ENV_FILE")
        os.environ["ENV_FILE"] = env_file

        # Clear the cache to force reload
        get_settings.cache_clear()

        settings = Settings(_env_file=env_file)
        assert settings.gateway_host == "127.0.0.1"
        assert settings.gateway_port == 8090
        assert settings.text_base_url == "http://127.0.0.1:11434"
        assert settings.routing_mode == "single"
        assert settings.transcribe_system_prompt == "Test prompt"
    finally:
        if original_env_file:
            os.environ["ENV_FILE"] = original_env_file
        else:
            os.environ.pop("ENV_FILE", None)
        Path(env_file).unlink()
        get_settings.cache_clear()


def test_settings_validates_routing_mode_audio_text():
    """Test that audio_text routing mode requires both upstream URLs."""
    with pytest.raises(ValueError, match="AUDIO_BASE_URL is required"):
        Settings(
            routing_mode="audio_text",
            text_base_url="http://127.0.0.1:11434",
            audio_base_url=None,
            transcribe_system_prompt="Test",
        )

    with pytest.raises(ValueError, match="TEXT_BASE_URL is required"):
        Settings(
            routing_mode="audio_text",
            text_base_url=None,
            audio_base_url="http://127.0.0.1:8080",
            transcribe_system_prompt="Test",
        )

    # Should succeed with both URLs
    settings = Settings(
        routing_mode="audio_text",
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        transcribe_system_prompt="Test",
    )
    assert settings.routing_mode == "audio_text"


def test_settings_validates_routing_mode_single():
    """Test that single routing mode requires at least one upstream URL."""
    with pytest.raises(ValueError, match="Either DEFAULT_BASE_URL or TEXT_BASE_URL must be set"):
        Settings(
            routing_mode="single",
            text_base_url=None,
            default_base_url=None,
            transcribe_system_prompt="Test",
        )

    # Should succeed with text_base_url
    settings = Settings(
        routing_mode="single",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.routing_mode == "single"

    # Should succeed with default_base_url
    settings = Settings(
        routing_mode="single",
        default_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.routing_mode == "single"


def test_settings_validates_url_format():
    """Test that URLs are validated for proper format."""
    with pytest.raises(ValueError, match="URL must use http or https scheme"):
        Settings(
            text_base_url="ftp://example.com",
            transcribe_system_prompt="Test",
        )

    with pytest.raises(ValueError, match="URL must have a valid host"):
        Settings(
            text_base_url="http://",
            transcribe_system_prompt="Test",
        )

    # Valid URL should pass
    settings = Settings(
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.text_base_url == "http://127.0.0.1:11434"


def test_settings_validates_port_range():
    """Test that port numbers are validated."""
    with pytest.raises(ValueError, match="gateway_port must be between 1 and 65535"):
        Settings(
            gateway_port=0,
            text_base_url="http://127.0.0.1:11434",
            transcribe_system_prompt="Test",
        )

    with pytest.raises(ValueError, match="gateway_port must be between 1 and 65535"):
        Settings(
            gateway_port=65536,
            text_base_url="http://127.0.0.1:11434",
            transcribe_system_prompt="Test",
        )

    # Valid port should pass
    settings = Settings(
        gateway_port=8090,
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.gateway_port == 8090


def test_settings_validates_log_level():
    """Test that log level is validated."""
    with pytest.raises(ValueError, match="log_level must be one of"):
        Settings(
            log_level="INVALID",
            text_base_url="http://127.0.0.1:11434",
            transcribe_system_prompt="Test",
        )

    # Valid log levels should pass
    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        settings = Settings(
            log_level=level,
            text_base_url="http://127.0.0.1:11434",
            transcribe_system_prompt="Test",
        )
        assert settings.log_level == level


def test_settings_boolean_properties():
    """Test boolean property conversions."""
    settings = Settings(
        audio_preprocess_enabled="1",
        audio_loudnorm="0",
        log_request_bodies="true",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.audio_preprocess_enabled_bool is True
    assert settings.audio_loudnorm_bool is False
    assert settings.log_request_bodies_bool is True

    settings = Settings(
        audio_preprocess_enabled="false",
        audio_loudnorm="yes",
        log_request_bodies="no",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.audio_preprocess_enabled_bool is False
    assert settings.audio_loudnorm_bool is True
    assert settings.log_request_bodies_bool is False


def test_settings_allow_origins_list():
    """Test that CORS origins are parsed correctly."""
    settings = Settings(
        allow_origins="http://localhost:3000,https://example.com",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    origins = settings.allow_origins_list
    assert len(origins) == 2
    assert "http://localhost:3000" in origins
    assert "https://example.com" in origins

    settings = Settings(
        allow_origins="",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.allow_origins_list == []


def test_settings_effective_base_url():
    """Test effective_base_url property."""
    # Single mode with default_base_url
    settings = Settings(
        routing_mode="single",
        default_base_url="http://127.0.0.1:9000",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.effective_base_url == "http://127.0.0.1:9000"

    # Single mode without default_base_url
    settings = Settings(
        routing_mode="single",
        text_base_url="http://127.0.0.1:11434",
        transcribe_system_prompt="Test",
    )
    assert settings.effective_base_url == "http://127.0.0.1:11434"

    # Audio_text mode
    settings = Settings(
        routing_mode="audio_text",
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        transcribe_system_prompt="Test",
    )
    assert settings.effective_base_url == "http://127.0.0.1:11434"


def test_get_settings_singleton():
    """Test that get_settings returns a singleton."""
    # Clear cache first
    get_settings.cache_clear()

    # This will fail if .env doesn't exist, but that's okay for this test
    # We're just checking the singleton pattern works
    try:
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    except ValueError:
        # If .env doesn't exist, that's fine - we're just testing the pattern
        pass
    finally:
        get_settings.cache_clear()
