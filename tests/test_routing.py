"""Tests for backend routing logic (has_audio_content + select_upstream_url)."""

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.routing import has_audio_content, select_upstream_url


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings_single():
    """Settings with routing_mode=single."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="single",
    )


@pytest.fixture
def settings_audio_text():
    """Settings with routing_mode=audio_text."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        audio_base_url="http://127.0.0.1:8080",
        routing_mode="audio_text",
    )


# ---------------------------------------------------------------------------
# has_audio_content
# ---------------------------------------------------------------------------

class TestHasAudioContent:
    """Tests for has_audio_content()."""

    def test_text_only_string_content(self):
        messages = [{"role": "user", "content": "Hello, world!"}]
        assert has_audio_content(messages) is False

    def test_input_audio_type(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": "base64..."}},
                ],
            }
        ]
        assert has_audio_content(messages) is True

    def test_audio_type_variant(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "audio": {"data": "base64..."}},
                ],
            }
        ]
        assert has_audio_content(messages) is True

    def test_mixed_text_and_audio(self):
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

    def test_empty_messages(self):
        assert has_audio_content([]) is False

    def test_multiple_messages_one_with_audio(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Some text"},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": "base64..."}},
                ],
            },
        ]
        assert has_audio_content(messages) is True

    def test_list_content_without_audio_types(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Just text"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
                ],
            }
        ]
        assert has_audio_content(messages) is False


# ---------------------------------------------------------------------------
# select_upstream_url
# ---------------------------------------------------------------------------

class TestSelectUpstreamUrl:
    """Tests for select_upstream_url()."""

    def test_single_mode_returns_effective_base_url(self, settings_single):
        body = {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
        url = select_upstream_url(body, settings_single)
        assert url == settings_single.effective_base_url

    def test_single_mode_missing_url_raises(self):
        mock = MagicMock()
        mock.routing_mode = "single"
        mock.effective_base_url = ""
        with pytest.raises(ValueError, match="No upstream URL configured"):
            select_upstream_url({}, mock)

    def test_audio_text_mode_text_request(self, settings_audio_text):
        body = {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
        url = select_upstream_url(body, settings_audio_text)
        assert url == "http://127.0.0.1:11434"

    def test_audio_text_mode_audio_request(self, settings_audio_text):
        body = {
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
        url = select_upstream_url(body, settings_audio_text)
        assert url == "http://127.0.0.1:8080"

    def test_audio_text_mode_missing_audio_url_raises(self):
        mock = MagicMock()
        mock.routing_mode = "audio_text"
        mock.audio_base_url = ""
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "input_audio", "input_audio": {"data": "x"}}],
                }
            ]
        }
        with pytest.raises(ValueError, match="AUDIO_BASE_URL is required"):
            select_upstream_url(body, mock)

    def test_audio_text_mode_missing_text_url_raises(self):
        mock = MagicMock()
        mock.routing_mode = "audio_text"
        mock.text_base_url = ""
        body = {"messages": [{"role": "user", "content": "Hi"}]}
        with pytest.raises(ValueError, match="TEXT_BASE_URL is required"):
            select_upstream_url(body, mock)
