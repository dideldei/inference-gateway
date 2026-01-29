# Inference Gateway - Core Library

This is the core library module. Copy this entire `inference_gateway/` folder to use the library in other projects.

## What's Inside

```
inference_gateway/
├── __init__.py              # Public API exports
└── core/                    # Core library (no FastAPI dependencies)
    ├── __init__.py
    ├── audio.py            # Audio preprocessing and normalization
    ├── client.py           # HTTP forwarding to upstream backends
    ├── config.py           # GatewayConfig dataclass
    ├── exceptions.py       # Custom exception types
    ├── operations.py       # High-level API (transcribe, analyze, chat)
    └── routing.py          # Backend routing logic
```

## Public API

Import from the package root:

```python
from inference_gateway import (
    GatewayConfig,
    transcribe_audio,
    analyze_audio,
    chat_completion,
    list_models,
)
```

## Module Overview

### config.py
Defines `GatewayConfig` dataclass for configuration.

```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",
    routing_mode="single",
    timeout_s=300.0,
    connect_timeout_s=10.0,
)
```

### operations.py
High-level async API functions:
- `transcribe_audio()` - Audio to text
- `analyze_audio()` - Analyze audio with instruction
- `chat_completion()` - OpenAI-compatible chat
- `list_models()` - List available models

### client.py
Low-level HTTP forwarding:
- `forward_chat_completion()` - Forward request to upstream
- `forward_models()` - Forward models list request

### audio.py
Audio processing utilities:
- `normalize_audio_to_wav()` - Normalize audio format/sample rate

### routing.py
Backend routing logic:
- `select_upstream_url()` - Select which backend to use

### exceptions.py
Custom exceptions:
- `UpstreamUnreachableError`
- `UpstreamTimeoutError`
- `InvalidRequestError`
- `ConfigurationError`

## Usage

### Basic Example

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

### With Error Handling

```python
from inference_gateway import GatewayConfig, transcribe_audio
from inference_gateway.core.exceptions import UpstreamUnreachableError, UpstreamTimeoutError

async def safe_transcribe(audio_file, config):
    try:
        with open(audio_file, "rb") as f:
            return await transcribe_audio(f.read(), config)
    except UpstreamUnreachableError:
        print("Server not running")
        return None
    except UpstreamTimeoutError:
        print("Server timeout")
        return None
```

## Dependencies

- `httpx>=0.25.0` - Async HTTP client
- `pydantic>=2.0.0` - Data validation

Optional:
- `ffmpeg` - For audio preprocessing (if `audio_preprocess_enabled=True`)

## To Use in Your Project

1. **Copy this folder** to your project
2. **Install dependencies:**
   ```bash
   pip install httpx pydantic
   ```
3. **Import and use:**
   ```python
   from inference_gateway import GatewayConfig, transcribe_audio
   ```

## Architecture Notes

- **No external dependencies** on FastAPI, uvicorn, or other frameworks
- **Pure async/await** throughout
- **OpenAI-compatible** request/response format
- **Minimal and focused** - only handles audio transcription and text generation
- **Backend agnostic** - works with any OpenAI-compatible API server

## Testing

The library is tested with:
- llama.cpp server (with Voxtral model + mmproj)
- Audio files in WAV format
- Async operation in various contexts (FastAPI, plain asyncio, etc.)

See parent project for test files and examples.
