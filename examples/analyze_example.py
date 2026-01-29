"""Example: Analyze audio with custom instructions using the inference gateway library."""

import asyncio

from inference_gateway import GatewayConfig, analyze_audio


async def main():
    """Analyze an audio file with a custom instruction."""
    # Configure the gateway
    config = GatewayConfig(
        audio_base_url="http://localhost:8080",
        routing_mode="single",
        audio_preprocess_enabled=True,
    )

    # Read audio file
    audio_path = "path/to/your/meeting.wav"
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    # Analyze with custom instruction
    instruction = "Summarize the key points and action items from this meeting recording."

    print("Analyzing audio...")
    result = await analyze_audio(audio_bytes, instruction, config)

    print(f"\nAnalysis Result:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
