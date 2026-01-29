"""Complete test: Transcribe and analyze WAV files from fixtures directory."""

import asyncio
from pathlib import Path
from inference_gateway import GatewayConfig, transcribe_audio, analyze_audio


async def transcribe_wav(file_path: str, config: GatewayConfig) -> str:
    """Transcribe a single WAV file."""
    print(f"   📝 Transcribing...")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    try:
        transcript = await transcribe_audio(audio_bytes, config)
        return transcript
    except Exception as e:
        print(f"   ❌ Transcription error: {e}")
        return None


async def analyze_wav(
    file_path: str,
    instruction: str,
    config: GatewayConfig,
) -> str:
    """Analyze a single WAV file with custom instruction."""

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    try:
        result = await analyze_audio(audio_bytes, instruction, config)
        return result
    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return None


async def main():
    """Complete test: Transcribe and analyze both WAV files."""
    print("🎙️  Inference Gateway - Complete WAV Processing Test\n")
    print("=" * 80)
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

    print(f"📁 Found {len(wav_files)} WAV file(s)")
    print()

    # Define analysis instructions
    analysis_instructions = [
        "Summarize the main topic and key points discussed in this audio",
        "Extract any names, numbers, dates, or important identifiers mentioned",
        "Describe the tone, mood, and context of the conversation",
    ]

    # Store results
    results = {}

    # ============================================================================
    # PHASE 1: TRANSCRIPTION
    # ============================================================================
    print("=" * 80)
    print("PHASE 1: TRANSCRIPTION")
    print("=" * 80)
    print()

    for wav_file in wav_files:
        print(f"📂 {wav_file.name}")
        size_mb = wav_file.stat().st_size / (1024 * 1024)
        print(f"   Size: {size_mb:.1f} MB")

        transcript = await transcribe_wav(str(wav_file), config)
        results[wav_file.name] = {
            "transcript": transcript,
            "analyses": {}
        }

        if transcript:
            print(f"   ✅ Transcription complete ({len(transcript)} characters)")
            # Show preview
            preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
            print(f"   Preview: {preview}")
        print()

    # ============================================================================
    # PHASE 2: ANALYSIS
    # ============================================================================
    print()
    print("=" * 80)
    print("PHASE 2: ANALYSIS")
    print("=" * 80)
    print()

    for wav_file in wav_files:
        print(f"📂 {wav_file.name}")

        for i, instruction in enumerate(analysis_instructions, 1):
            print(f"   [{i}/{len(analysis_instructions)}] {instruction[:60]}...")

            analysis = await analyze_wav(str(wav_file), instruction, config)
            results[wav_file.name]["analyses"][instruction] = analysis

            if analysis:
                print(f"       ✅ Analysis complete ({len(analysis)} characters)")
            print()

    # ============================================================================
    # PHASE 3: SUMMARY & EXPORT
    # ============================================================================
    print()
    print("=" * 80)
    print("PHASE 3: RESULTS SUMMARY")
    print("=" * 80)
    print()

    # Count successes
    total_transcriptions = len(wav_files)
    successful_transcriptions = sum(
        1 for r in results.values() if r["transcript"] is not None
    )

    total_analyses = len(wav_files) * len(analysis_instructions)
    successful_analyses = sum(
        1 for analyses in [r["analyses"] for r in results.values()]
        for result in analyses.values()
        if result is not None
    )

    print(f"📊 Transcriptions: {successful_transcriptions}/{total_transcriptions} successful")
    print(f"📊 Analyses: {successful_analyses}/{total_analyses} successful")
    print()

    # Detailed results
    for filename, data in results.items():
        print(f"\n{'=' * 80}")
        print(f"📄 {filename}")
        print(f"{'=' * 80}")

        # Transcription
        if data["transcript"]:
            print(f"\n✅ TRANSCRIPTION ({len(data['transcript'])} characters):")
            print("-" * 80)
            print(data["transcript"])
            print("-" * 80)
        else:
            print(f"\n❌ TRANSCRIPTION: Failed")

        # Analyses
        print(f"\n📊 ANALYSES:")
        for i, (instruction, analysis) in enumerate(data["analyses"].items(), 1):
            print(f"\n   [{i}] {instruction}")
            if analysis:
                print(f"   Status: ✅ Complete ({len(analysis)} characters)")
                print(f"   " + "-" * 76)
                # Print with indentation
                for line in analysis.split('\n'):
                    print(f"   {line}")
                print(f"   " + "-" * 76)
            else:
                print(f"   Status: ❌ Failed")

    # Final summary
    print()
    print("=" * 80)
    print("🎉 COMPLETE!")
    print("=" * 80)
    print(f"\nTotal successful operations: {successful_transcriptions + successful_analyses}")
    print(f"Total operations: {total_transcriptions + total_analyses}")
    print()

    if successful_transcriptions == total_transcriptions and successful_analyses == total_analyses:
        print("✅ All operations completed successfully!")
        return 0
    else:
        print(f"⚠️  Some operations failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
