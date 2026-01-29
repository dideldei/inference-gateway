# Inference Gateway — Python Library

A lightweight Python library for audio transcription and text generation using OpenAI-compatible APIs.

**Supports:** Voxtral (audio transcription + analysis) via llama.cpp

## Features

- **🎙️ Audio Transcription** - Transcribe audio files to text
- **📊 Audio Analysis** - Analyze audio with custom instructions (summarize, extract info, etc.)
- **💬 Chat Completion** - Text generation with OpenAI-compatible API
- **⚡ Async/Await** - Full async support for high performance
- **📦 Minimal Dependencies** - Just httpx + pydantic
- **🔄 Single Model** - One unified model handles transcription + analysis

## Installation

```bash
pip install inference-gateway
```

## Quick Start

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio, analyze_audio, chat_completion

config = GatewayConfig(text_base_url="http://localhost:8080")

# Transcribe audio
async def main():
    with open("audio.wav", "rb") as f:
        transcript = await transcribe_audio(f.read(), config)
    print(transcript)

asyncio.run(main())
```

## Server Setup

### Quick Start (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\start_server.ps1
```

**Linux / macOS:**
```bash
./scripts/start_server.sh
```

### Manual Start

```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

### Verify Server

```bash
curl http://localhost:8080/health
# Returns: {"status":"ok"}
```

See [scripts/README.md](scripts/README.md) for more options and troubleshooting.

## Documentation

- **[USAGE.md](USAGE.md)** — Complete usage guide with examples
- **[LIBRARY_USAGE.md](LIBRARY_USAGE.md)** — API reference
- **[examples/](examples/)** — Code examples

## API Overview

```python
# Transcribe
transcript = await transcribe_audio(audio_bytes, config)

# Analyze audio
result = await analyze_audio(audio_bytes, "Summarize this", config)

# Chat/Text generation
response = await chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    config=config,
)
text = response["choices"][0]["message"]["content"]
```

## Requirements

- Python 3.11+
- llama.cpp server with Voxtral model
- httpx, pydantic (auto-installed)

## License

MIT License - see [LICENSE](LICENSE) for details
