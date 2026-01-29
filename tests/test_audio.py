"""Tests for audio preprocessing module."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.audio import AudioPreprocessError, _build_ffmpeg_cmd, normalize_audio_to_wav
from app.config import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_WAV = FIXTURES_DIR / "27.01.26_16.13_Anruf.01627639696.wav"


@pytest.fixture
def audio_settings():
    """Settings with audio preprocessing enabled."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        routing_mode="single",
        audio_preprocess_enabled="1",
        audio_loudnorm="1",
        audio_loudnorm_filter="loudnorm=I=-16:TP=-1.5:LRA=11",
        audio_target_sr=16000,
        audio_target_channels=1,
        audio_max_upload_bytes=1_000_000,
    )


@pytest.fixture
def audio_settings_no_loudnorm():
    """Settings with loudnorm disabled."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        routing_mode="single",
        audio_preprocess_enabled="1",
        audio_loudnorm="0",
        audio_target_sr=16000,
        audio_target_channels=1,
        audio_max_upload_bytes=1_000_000,
    )


@pytest.fixture
def audio_settings_disabled():
    """Settings with audio preprocessing disabled."""
    return Settings(
        text_base_url="http://127.0.0.1:11434",
        routing_mode="single",
        audio_preprocess_enabled="0",
        audio_max_upload_bytes=1_000_000,
    )


# --- Size gate ---


@pytest.mark.asyncio
async def test_rejects_oversized_input(audio_settings):
    """Oversized input raises AudioPreprocessError with audio_too_large type."""
    data = b"\x00" * (audio_settings.audio_max_upload_bytes + 1)
    with pytest.raises(AudioPreprocessError) as exc_info:
        await normalize_audio_to_wav(data, audio_settings)
    assert exc_info.value.error_type == "audio_too_large"


# --- Preprocessing disabled ---


@pytest.mark.asyncio
async def test_disabled_returns_input_unchanged(audio_settings_disabled):
    """When preprocessing is disabled, input bytes are returned as-is."""
    data = b"raw audio bytes"
    result = await normalize_audio_to_wav(data, audio_settings_disabled)
    assert result == data


# --- ffmpeg command construction ---


def test_ffmpeg_cmd_with_loudnorm(audio_settings):
    """Command includes -af loudnorm filter when enabled."""
    cmd = _build_ffmpeg_cmd("/tmp/in", "/tmp/out.wav", audio_settings)
    assert "-af" in cmd
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in cmd
    assert "-ac" in cmd
    assert "1" in cmd
    assert "-ar" in cmd
    assert "16000" in cmd


def test_ffmpeg_cmd_without_loudnorm(audio_settings_no_loudnorm):
    """Command omits -af when loudnorm is disabled."""
    cmd = _build_ffmpeg_cmd("/tmp/in", "/tmp/out.wav", audio_settings_no_loudnorm)
    assert "-af" not in cmd


# --- Successful normalization ---


@pytest.mark.asyncio
async def test_normalize_success(audio_settings):
    """Happy path: ffmpeg succeeds and output WAV bytes are returned."""
    input_data = b"fake audio"
    output_data = b"RIFF....WAVEfmt normalized"

    def fake_run(cmd):
        output_path = cmd[-1]
        Path(output_path).write_bytes(output_data)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

    with patch("app.audio._run_ffmpeg", side_effect=fake_run):
        result = await normalize_audio_to_wav(input_data, audio_settings)

    assert result == output_data


# --- ffmpeg failure ---


@pytest.mark.asyncio
async def test_ffmpeg_failure_raises_error(audio_settings):
    """Non-zero return code raises AudioPreprocessError with invalid_audio type."""
    failed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout=b"", stderr=b"Error decoding"
    )

    with patch("app.audio._run_ffmpeg", return_value=failed):
        with pytest.raises(AudioPreprocessError) as exc_info:
            await normalize_audio_to_wav(b"bad data", audio_settings)
        assert exc_info.value.error_type == "invalid_audio"


# --- ffmpeg timeout ---


@pytest.mark.asyncio
async def test_ffmpeg_timeout_raises_error(audio_settings):
    """TimeoutExpired raises AudioPreprocessError with audio_timeout type."""
    with patch(
        "app.audio._run_ffmpeg",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=60),
    ):
        with pytest.raises(AudioPreprocessError) as exc_info:
            await normalize_audio_to_wav(b"slow data", audio_settings)
        assert exc_info.value.error_type == "audio_timeout"


# --- Temp file cleanup ---


@pytest.mark.asyncio
async def test_temp_files_cleaned_on_success(audio_settings):
    """Temp directory is removed after successful normalization."""
    created_dirs = []
    original_mkdtemp = __import__("tempfile").mkdtemp

    def tracking_mkdtemp(**kwargs):
        d = original_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    def fake_run(cmd):
        Path(cmd[-1]).write_bytes(b"wav output")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=b"", stderr=b"")

    with patch("app.audio.tempfile.mkdtemp", side_effect=tracking_mkdtemp):
        with patch("app.audio._run_ffmpeg", side_effect=fake_run):
            await normalize_audio_to_wav(b"input", audio_settings)

    assert len(created_dirs) == 1
    assert not Path(created_dirs[0]).exists()


@pytest.mark.asyncio
async def test_temp_files_cleaned_on_failure(audio_settings):
    """Temp directory is removed even when ffmpeg fails."""
    created_dirs = []
    original_mkdtemp = __import__("tempfile").mkdtemp

    def tracking_mkdtemp(**kwargs):
        d = original_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    failed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout=b"", stderr=b"error"
    )

    with patch("app.audio.tempfile.mkdtemp", side_effect=tracking_mkdtemp):
        with patch("app.audio._run_ffmpeg", return_value=failed):
            with pytest.raises(AudioPreprocessError):
                await normalize_audio_to_wav(b"input", audio_settings)

    assert len(created_dirs) == 1
    assert not Path(created_dirs[0]).exists()


# --- Integration test with real fixture (requires ffmpeg) ---


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)
@pytest.mark.skipif(
    not TEST_WAV.exists(), reason="test fixture not found"
)
@pytest.mark.asyncio
async def test_normalize_real_wav_fixture(audio_settings):
    """Integration: normalize the real test WAV fixture with ffmpeg."""
    audio_settings.audio_max_upload_bytes = 50_000_000  # fixture may be large
    input_bytes = TEST_WAV.read_bytes()
    result = await normalize_audio_to_wav(input_bytes, audio_settings)

    # Output should be a valid WAV (starts with RIFF header)
    assert result[:4] == b"RIFF"
    assert b"WAVE" in result[:12]
    assert len(result) > 0
