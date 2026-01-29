"""Test transcribing WAV files from fixtures directory."""

import asyncio
import json
from pathlib import Path
from inference_gateway import GatewayConfig, transcribe_audio


async def transcribe_wav(file_path: str, config: GatewayConfig) -> str:
    """Transcribe a single WAV file."""
    print(f"📂 Loading: {file_path}")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    file_size_mb = len(audio_bytes) / (1024 * 1024)
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"   Transcribing...")

    try:
        transcript = await transcribe_audio(audio_bytes, config)
        print(f"✅ Success!")
        return transcript
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def main():
    """Transcribe both WAV files."""
    print("🎙️  Inference Gateway - WAV Transcription Test\n")
    print("=" * 70)
    print()

    # Configure for llama.cpp
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        routing_mode="single",
    )

    print("📋 Configuration:")
    print(f"   Server: {config.text_base_url}")
    print(f"   Routing: {config.routing_mode}")
    print()

    # Find WAV files in fixtures
    fixtures_dir = Path("tests/fixtures")
    wav_files = sorted(fixtures_dir.glob("*.wav"))

    if not wav_files:
        print(f"❌ No WAV files found in {fixtures_dir}")
        return 1

    print(f"📁 Found {len(wav_files)} WAV file(s):")
    for i, f in enumerate(wav_files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   [{i}] {f.name} ({size_mb:.1f} MB)")
    print()

    # Process each file
    results = {}
    for wav_file in wav_files:
        print(f"\n{'=' * 70}")
        print(f"Processing: {wav_file.name}")
        print("=" * 70)

        transcript = await transcribe_wav(str(wav_file), config)
        results[wav_file.name] = transcript

        if transcript:
            print()
            print("📝 Transcript:")
            print("-" * 70)
            print(transcript)
            print("-" * 70)
        print()

    # Summary
    print()
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)

    successful = sum(1 for t in results.values() if t is not None)
    total = len(results)

    print(f"✅ Successful: {successful}/{total}")
    print()

    for filename, transcript in results.items():
        status = "✅" if transcript else "❌"
        print(f"{status} {filename}")
        if transcript:
            # Show first 100 chars
            preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
            print(f"   → {preview}")

    print()

    if successful == total:
        print("🎉 All files transcribed successfully!")
        return 0
    else:
        print(f"⚠️  {total - successful} file(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
