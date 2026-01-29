"""Test analyzing WAV files from fixtures directory."""

import asyncio
from pathlib import Path
from inference_gateway import GatewayConfig, analyze_audio


async def analyze_wav(
    file_path: str,
    instruction: str,
    config: GatewayConfig,
) -> str:
    """Analyze a single WAV file with custom instruction."""
    print(f"📂 Loading: {file_path}")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    file_size_mb = len(audio_bytes) / (1024 * 1024)
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"   Instruction: {instruction}")
    print(f"   Analyzing...")

    try:
        result = await analyze_audio(audio_bytes, instruction, config)
        print(f"✅ Success!")
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def main():
    """Analyze both WAV files."""
    print("🎙️  Inference Gateway - WAV Analysis Test\n")
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

    # Define analysis instructions
    instructions = [
        "Summarize the main topic and key points discussed in this audio",
        "Extract any names, numbers, dates, or important identifiers mentioned",
        "Describe the tone, mood, and context of the conversation",
    ]

    # Process each file with each instruction
    results = {}

    for wav_file in wav_files:
        print(f"\n{'=' * 70}")
        print(f"Processing: {wav_file.name}")
        print("=" * 70)

        results[wav_file.name] = {}

        for i, instruction in enumerate(instructions, 1):
            print(f"\n[Analysis {i}/{len(instructions)}]")
            print("-" * 70)

            analysis = await analyze_wav(str(wav_file), instruction, config)
            results[wav_file.name][instruction] = analysis

            if analysis:
                print()
                print("📊 Analysis Result:")
                print("-" * 70)
                print(analysis)
                print("-" * 70)
            print()

    # Summary
    print()
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)

    total_analyses = len(wav_files) * len(instructions)
    successful = sum(
        1 for analyses in results.values()
        for result in analyses.values()
        if result is not None
    )

    print(f"✅ Successful: {successful}/{total_analyses}")
    print()

    for filename, analyses in results.items():
        print(f"\n📄 {filename}:")
        for i, (instruction, result) in enumerate(analyses.items(), 1):
            status = "✅" if result else "❌"
            print(f"  {status} Analysis {i}: {instruction[:50]}...")
            if result:
                preview = result[:80] + "..." if len(result) > 80 else result
                print(f"      → {preview}")

    print()

    if successful == total_analyses:
        print("🎉 All analyses completed successfully!")
        return 0
    else:
        print(f"⚠️  {total_analyses - successful} analysis/analyses failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
