"""Audio preprocessing utilities using ffmpeg for normalization."""

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from inference_gateway.core.config import GatewayConfig
from inference_gateway.core.exceptions import AudioProcessingError

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_S = 60


def _build_ffmpeg_cmd(
    input_path: str, output_path: str, config: GatewayConfig
) -> list[str]:
    """Build a deterministic ffmpeg command array from config."""
    cmd = [
        config.ffmpeg_bin,
        "-y",
        "-i", input_path,
        "-ac", str(config.audio_target_channels),
        "-ar", str(config.audio_target_sr),
    ]
    if config.audio_loudnorm_bool:
        cmd.extend(["-af", config.audio_loudnorm_filter])
    cmd.extend(["-f", "wav", output_path])
    return cmd


def _run_ffmpeg(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run ffmpeg synchronously. Intended to be called via asyncio.to_thread."""
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=FFMPEG_TIMEOUT_S,
    )


async def normalize_audio_to_wav(input_bytes: bytes, config: GatewayConfig) -> bytes:
    """Normalize audio bytes to WAV PCM using ffmpeg.

    Args:
        input_bytes: Raw audio bytes in any format ffmpeg can decode.
        config: Gateway configuration for ffmpeg settings.

    Returns:
        Normalized WAV bytes.

    Raises:
        AudioProcessingError: On size limit, ffmpeg failure, or timeout.
    """
    if len(input_bytes) > config.audio_max_upload_bytes:
        raise AudioProcessingError(
            f"Audio upload exceeds maximum size of {config.audio_max_upload_bytes} bytes",
            error_type="audio_too_large",
        )

    if not config.audio_preprocess_enabled_bool:
        return input_bytes

    temp_dir = tempfile.mkdtemp(prefix="gateway_audio_")
    try:
        input_path = str(Path(temp_dir) / "input")
        output_path = str(Path(temp_dir) / "output.wav")

        Path(input_path).write_bytes(input_bytes)

        cmd = _build_ffmpeg_cmd(input_path, output_path, config)
        logger.debug("Running ffmpeg: %s", " ".join(cmd))

        try:
            result = await asyncio.to_thread(_run_ffmpeg, cmd)
        except subprocess.TimeoutExpired:
            raise AudioProcessingError(
                "ffmpeg timed out while processing audio",
                error_type="audio_timeout",
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error("ffmpeg failed (rc=%d): %s", result.returncode, stderr)
            raise AudioProcessingError(
                "ffmpeg failed to decode input audio",
                error_type="invalid_audio",
            )

        return Path(output_path).read_bytes()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
