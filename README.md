# Inference Gateway — Python Library

A lightweight Python library for interacting with OpenAI-compatible inference backends, with support for audio preprocessing, intelligent routing, and high-level operations like transcription and analysis.

## Features

- **🎯 Simple API** - Async functions for transcription, analysis, and chat completion
- **🔊 Audio Preprocessing** - Automatic audio normalization with ffmpeg (optional)
- **🔀 Intelligent Routing** - Route requests to different backends based on content
- **🔌 OpenAI Compatible** - Works with any OpenAI-compatible inference backend
- **📦 Minimal Dependencies** - Just httpx + pydantic
- **⚡ Async/Await** - Full async support for high performance

## Installation

```bash
pip install inference-gateway
```

## Quick Start

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio

async def main():
    # Configure
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        audio_preprocess_enabled=True,
    )
    
    # Load audio
    with open("recording.mp3", "rb") as f:
        audio_bytes = f.read()
    
    # Transcribe
    transcript = await transcribe_audio(audio_bytes, config)
    print(f"Transcript: {transcript}")

# Run
asyncio.run(main())
```

## Documentation

- **[LIBRARY_USAGE.md](LIBRARY_USAGE.md)** — Complete API reference with examples
- **[examples/](examples/)** — Working code examples (transcribe, analyze, chat)
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** — What changed in v0.2.0

## For v0.1.0 Users

If you're using the **server mode** from v0.1.0, you have options:

1. **Continue with v0.1.0** - Pin your dependency:
   ```bash
   pip install 'inference-gateway==0.1.0'
   ```

2. **Use the library** - Integrate into your Python application (recommended):
   ```python
   from inference_gateway import GatewayConfig, transcribe_audio
   ```

3. **Build your own server** - Use the library in a FastAPI wrapper:
   ```python
   from fastapi import FastAPI, UploadFile
   from inference_gateway import GatewayConfig, transcribe_audio
   
   app = FastAPI()
   config = GatewayConfig(text_base_url="http://localhost:8080")
   
   @app.post("/transcribe")
   async def transcribe(file: UploadFile):
       audio = await file.read()
       transcript = await transcribe_audio(audio, config)
       return {"transcript": transcript}
   ```

See [app/](app/) for the original v0.1.0 server code.

## Requirements

- Python 3.11 or higher
- httpx (installed automatically)
- pydantic (installed automatically)
- Optional: ffmpeg (for audio preprocessing)

## License

[Add license here]
