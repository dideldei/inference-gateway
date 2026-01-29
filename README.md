# Inference Gateway — Python Library

A lightweight async Python library for audio transcription and text generation using OpenAI-compatible APIs.

**Supports:** Voxtral (audio transcription + analysis) via llama.cpp

## Features

- **🎙️ Audio Transcription** - Transcribe audio files to text
- **📊 Audio Analysis** - Analyze audio with custom instructions
- **💬 Chat Completion** - Text generation with OpenAI-compatible API
- **⚡ Async/Await** - Full async support for high performance
- **📦 Minimal Dependencies** - Just httpx + pydantic
- **🔄 Single Model** - One unified model for all operations

## Installation

```bash
pip install inference-gateway
```

## Quick Example

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio

async def main():
    config = GatewayConfig(text_base_url="http://localhost:8080")
    
    with open("audio.wav", "rb") as f:
        transcript = await transcribe_audio(f.read(), config)
    
    print(transcript)

asyncio.run(main())
```

## Documentation

| Guide | Purpose |
|-------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get started in 5 minutes |
| **[USAGE_GUIDE.md](USAGE_GUIDE.md)** | Complete API reference & examples |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Design & internals |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues & solutions |
| **[scripts/README.md](scripts/README.md)** | Server setup & scripts |

## Requirements

- Python 3.11+
- llama.cpp server with Voxtral model
- httpx, pydantic (auto-installed)
- Optional: ffmpeg (for audio preprocessing)

## API Overview

### Transcription

```python
transcript = await transcribe_audio(audio_bytes, config)
```

### Analysis

```python
analysis = await analyze_audio(audio_bytes, instruction, config)
```

### Chat Completion

```python
response = await chat_completion(messages, config)
text = response["choices"][0]["message"]["content"]
```

See [USAGE_GUIDE.md](USAGE_GUIDE.md) for complete API reference.

## Server Setup

Quick start with scripts:

**Windows:**
```powershell
.\scripts\start_server.ps1
```

**Linux/macOS:**
```bash
./scripts/start_server.sh
```

Or manually:
```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

See [scripts/README.md](scripts/README.md) for detailed options.

## Getting Started

1. **New to the library?** → Start with [QUICKSTART.md](QUICKSTART.md)
2. **Need complete reference?** → Read [USAGE_GUIDE.md](USAGE_GUIDE.md)
3. **Having issues?** → Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Want to understand design?** → See [ARCHITECTURE.md](ARCHITECTURE.md)

## Examples

See `examples/` directory for complete runnable examples:
- `chat_example.py` - Chat completions
- `transcribe_example.py` - Audio transcription
- `analyze_example.py` - Audio analysis

## License

MIT License - see [LICENSE](LICENSE) for details
