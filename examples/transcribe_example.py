"""Example: Transcribe an audio file using the inference gateway library."""

import asyncio

from inference_gateway import GatewayConfig, transcribe_audio


async def main():
    """Transcribe an audio file."""
    # Configure the gateway to point to your inference backend
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        audio_preprocess_enabled=True,  # Enable ffmpeg preprocessing
        audio_target_sr=16000,  # 16kHz sample rate
        audio_target_channels=1,  # Mono audio
    )

    # Read audio file
    audio_path = "path/to/your/audio.mp3"
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    # Transcribe
    print("Transcribing audio...")
    transcript = await transcribe_audio(audio_bytes, config)

    print(f"\nTranscript:\n{transcript}")


if __name__ == "__main__":
    asyncio.run(main())
