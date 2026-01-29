# Inference Gateway - Complete Usage Guide

A lightweight Python library for audio transcription and text generation using OpenAI-compatible APIs.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [API Reference](#api-reference)
5. [Common Patterns](#common-patterns)
6. [Audio Preprocessing](#audio-preprocessing)
7. [Error Handling](#error-handling)
8. [Advanced Usage](#advanced-usage)
9. [Server Setup](#server-setup)
10. [Logging](#logging)
11. [Examples](#examples)

## Installation

```bash
pip install inference-gateway
```

For development:
```bash
git clone <repository>
cd inference-gateway
pip install -e .
```

## Quick Start

### 1. Start the Server

```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

**Important:** The `-hf` flag automatically downloads and loads the mmproj (audio encoder) which is **required** for audio transcription and analysis.

### 2. Basic Chat Completion

```python
import asyncio
from inference_gateway import GatewayConfig, chat_completion

async def main():
    config = GatewayConfig(text_base_url="http://localhost:8080")
    
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    response = await chat_completion(messages, config)
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

### 3. Audio Transcription

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio

async def main():
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        audio_preprocess_enabled=True,  # Enable audio preprocessing
    )
    
    with open("audio.wav", "rb") as f:
        transcript = await transcribe_audio(f.read(), config)
    print(f"Transcript: {transcript}")

asyncio.run(main())
```

### 4. Audio Analysis

```python
import asyncio
from inference_gateway import GatewayConfig, analyze_audio

async def main():
    config = GatewayConfig(text_base_url="http://localhost:8080")
    
    with open("meeting.wav", "rb") as f:
        audio_bytes = f.read()
    
    result = await analyze_audio(
        audio_bytes,
        instruction="Summarize the key points and action items",
        config=config,
    )
    print(f"Summary: {result}")

asyncio.run(main())
```

## Configuration

### GatewayConfig Parameters

```python
from inference_gateway import GatewayConfig

config = GatewayConfig(
    # Required
    text_base_url="http://localhost:8080",
    
    # Optional: Routing & Upstreams
    audio_base_url="http://localhost:8081",  # For dual-mode routing
    routing_mode="single",  # or "audio_text"
    
    # Timeouts
    timeout_s=300.0,  # Total timeout (seconds)
    connect_timeout_s=10.0,  # Connection timeout (seconds)
    
    # Audio preprocessing
    audio_preprocess_enabled=False,  # Set True to enable ffmpeg
    audio_max_upload_bytes=20_000_000,  # 20 MB default
    audio_target_sr=16000,  # Sample rate in Hz
    audio_target_channels=1,  # 1=mono, 2=stereo
    audio_loudnorm=True,  # Enable loudness normalization
    ffmpeg_bin="ffmpeg",  # Path to ffmpeg binary
    
    # Prompts
    transcribe_system_prompt="You are a helpful assistant that transcribes audio.",
    analyze_system_prompt_prefix="",
)
```

### Routing Modes

**Single Mode** (`routing_mode="single"`):
- All requests go to `text_base_url`
- Simplest configuration
- Use when you have one inference backend

**Audio/Text Mode** (`routing_mode="audio_text"`):
- Text requests → `text_base_url`
- Audio requests → `audio_base_url`
- Automatically detects audio content in messages
- Use when you have separate backends for text and audio

---

## API Reference

### High-Level Operations

#### `transcribe_audio(audio_bytes, config, system_prompt=None)`

Transcribe audio to text.

**Parameters:**
- `audio_bytes` (bytes): Raw audio data (any format ffmpeg supports)
- `config` (GatewayConfig): Configuration object
- `system_prompt` (str, optional): Custom system prompt

**Returns:**
- `str`: Transcript text

**Raises:**
- `AudioProcessingError`: If audio preprocessing fails
- `UpstreamError`: If upstream request fails
- `InvalidRequestError`: If response is malformed

**Example:**
```python
transcript = await transcribe_audio(
    audio_bytes,
    config,
    system_prompt="Transcribe this audio in Spanish",
)
```

#### `analyze_audio(audio_bytes, instruction, config, system_prompt_prefix=None)`

Analyze audio with a custom instruction.

**Parameters:**
- `audio_bytes` (bytes): Raw audio data
- `instruction` (str): Analysis instruction (e.g., "Summarize key points")
- `config` (GatewayConfig): Configuration object
- `system_prompt_prefix` (str, optional): Prefix for system prompt

**Returns:**
- `str`: Analysis result text

**Raises:**
- `AudioProcessingError`: If audio preprocessing fails
- `UpstreamError`: If upstream request fails

**Example:**
```python
summary = await analyze_audio(
    audio_bytes,
    instruction="List all speakers and their main points",
    config=config,
)
```

#### `chat_completion(messages, config, **openai_params)`

Send a chat completion request (OpenAI-compatible).

**Parameters:**
- `messages` (list[dict]): OpenAI-format message list
- `config` (GatewayConfig): Configuration object
- `**openai_params`: Additional OpenAI parameters (temperature, max_tokens, model, etc.)

**Returns:**
- `dict`: Full OpenAI-format response

**Example:**
```python
response = await chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"}
    ],
    config=config,
    temperature=0.7,
    max_tokens=100,
)

# Access response
content = response["choices"][0]["message"]["content"]
tokens_used = response["usage"]["total_tokens"]
```

#### `list_models(config)`

List available models from upstream.

**Parameters:**
- `config` (GatewayConfig): Configuration object

**Returns:**
- `dict`: OpenAI-format models list

**Example:**
```python
models = await list_models(config)
for model in models["data"]:
    print(f"Model: {model['id']}")
```

---

## Common Patterns

### Batch Processing (Concurrent)

Process multiple audio files in parallel:

```python
import asyncio
from pathlib import Path

async def transcribe_batch(audio_dir: str, config: GatewayConfig):
    """Transcribe all audio files in a directory."""
    audio_files = Path(audio_dir).glob("*.mp3")
    
    tasks = []
    for audio_path in audio_files:
        audio_bytes = audio_path.read_bytes()
        task = transcribe_audio(audio_bytes, config)
        tasks.append((audio_path.name, task))
    
    results = await asyncio.gather(*[task for _, task in tasks])
    return dict(zip([name for name, _ in tasks], results))

# Usage
transcripts = await transcribe_batch("recordings/", config)
for filename, transcript in transcripts.items():
    print(f"{filename}: {transcript[:100]}...")
```

### Error Handling

```python
async def safe_transcribe(audio_file: str, config: GatewayConfig) -> str | None:
    try:
        with open(audio_file, "rb") as f:
            return await transcribe_audio(f.read(), config)
    except FileNotFoundError:
        print(f"File not found: {audio_file}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
```

### FastAPI Integration

```python
from fastapi import FastAPI, UploadFile
from inference_gateway import GatewayConfig, transcribe_audio

app = FastAPI()
config = GatewayConfig(text_base_url="http://localhost:8080")

@app.post("/transcribe")
async def api_transcribe(file: UploadFile):
    content = await file.read()
    transcript = await transcribe_audio(content, config)
    return {"transcript": transcript}

@app.post("/analyze")
async def api_analyze(file: UploadFile, instruction: str):
    content = await file.read()
    result = await analyze_audio(content, instruction, config)
    return {"result": result}
```

---

## Audio Preprocessing

The library supports automatic audio preprocessing using ffmpeg.

### When to Enable

Enable preprocessing if you need to:
- Convert audio formats (MP3, M4A, OGG → WAV)
- Normalize sample rates (e.g., 44.1kHz → 16kHz)
- Convert stereo to mono
- Normalize loudness levels

### Configuration

```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",
    audio_preprocess_enabled=True,  # Enable preprocessing
    audio_target_sr=16000,  # Target 16kHz
    audio_target_channels=1,  # Convert to mono
    audio_loudnorm=True,  # Normalize loudness
    ffmpeg_bin="/usr/bin/ffmpeg",  # Custom ffmpeg path
)
```

### Requirements

`ffmpeg` must be installed and accessible:

**Linux:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/

### Without Preprocessing

If preprocessing is disabled:
- Audio is passed as-is to the upstream
- Upstream must handle format detection
- Faster, no ffmpeg required

---

## Error Handling

The library provides specific exception types:

```python
from inference_gateway import (
    AudioProcessingError,
    ConfigurationError,
    UpstreamUnreachableError,
    UpstreamTimeoutError,
    InvalidRequestError,
)

try:
    transcript = await transcribe_audio(audio_bytes, config)
except AudioProcessingError as e:
    print(f"Audio processing failed: {e.message}")
    print(f"Error type: {e.error_type}")
except UpstreamUnreachableError as e:
    print(f"Cannot reach upstream: {e.upstream}")
except UpstreamTimeoutError as e:
    print(f"Upstream timeout: {e.upstream}")
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
except InvalidRequestError as e:
    print(f"Invalid response: {e.message}")
```

---

## Advanced Usage

### Custom Timeout Configuration

For long-running inference operations:

```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",
    timeout_s=600.0,  # 10 minutes for long-running inference
    connect_timeout_s=30.0,  # 30s connection timeout
)
```

### Working with Audio Content in Messages

Send audio content directly in chat messages:

```python
import base64

# Encode audio
with open("audio.wav", "rb") as f:
    audio_bytes = f.read()
b64_audio = base64.b64encode(audio_bytes).decode("ascii")

# Create message with audio
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "input_audio",
                "input_audio": {"data": b64_audio, "format": "wav"}
            }
        ]
    }
]

# Send via chat_completion
response = await chat_completion(messages, config)
```

### Custom System Prompts

Override default prompts for specific operations:

```python
# Transcription with custom prompt
transcript = await transcribe_audio(
    audio_bytes,
    config,
    system_prompt="Transcribe this German conversation verbatim",
)

# Analysis with custom prefix
analysis = await analyze_audio(
    audio_bytes,
    instruction="Identify speakers and topics",
    config=config,
    system_prompt_prefix="You are a meeting analyst.",
)
```

---

## Server Setup

### Quick Start with Scripts

**Windows (PowerShell):**
```powershell
.\scripts\start_server.ps1
```

**Linux / macOS:**
```bash
./scripts/start_server.sh
```

See [scripts/README.md](scripts/README.md) for detailed options and troubleshooting.

### Manual Start

```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

### Verify Server

```bash
curl http://localhost:8080/health
# Returns: {"status":"ok"}
```

---

## Logging

The library uses Python's standard logging. Configure it in your application:

```python
import logging
from inference_gateway.core.logging import setup_logging

# Use the library's logging setup
setup_logging(level="DEBUG")

# Or configure manually
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inference_gateway")
logger.setLevel(logging.DEBUG)
```

---

## Examples

See the `examples/` directory for complete, runnable examples:

- `chat_example.py` - Chat completions
- `transcribe_example.py` - Audio transcription
- `analyze_example.py` - Audio analysis

### Running Examples

```bash
python examples/chat_example.py
python examples/transcribe_example.py
python examples/analyze_example.py
```

---

## Project Structure

```
inference_gateway/
├── __init__.py                 # Public API
├── core/
│   ├── audio.py               # Audio preprocessing
│   ├── client.py              # HTTP forwarding
│   ├── config.py              # Configuration
│   ├── exceptions.py          # Custom exceptions
│   ├── operations.py          # High-level API
│   └── routing.py             # Backend routing
└── utils/
    └── logging.py             # Logging setup
```

---

## Performance

- **Transcription:** ~5-10 seconds per minute of audio
- **Analysis:** ~3-5 seconds
- **Batch processing:** Use `asyncio.gather()` for parallel processing
- **Concurrent requests:** Server supports multiple parallel requests

---

## Dependencies

**Required:**
- `httpx>=0.25.0` - Async HTTP client
- `pydantic>=2.0.0` - Data validation

**Optional:**
- `ffmpeg` - For audio preprocessing (if enabled)

---

## Migration from Server Mode (v0.1.0)

If you were using v0.1.0 as a server, you have options:

**Option 1: Use the library directly in your application**
```python
# Old: HTTP POST to /v1/transcribe
# New: Direct function call
transcript = await transcribe_audio(audio_bytes, config)
```

**Option 2: Keep using v0.1.0 server**
- Pin to version `0.1.0` in requirements
- The old `app/` code still works as a FastAPI server

**Option 3: Build your own server wrapper**
```python
from fastapi import FastAPI, File, UploadFile
from inference_gateway import GatewayConfig, transcribe_audio

app = FastAPI()
config = GatewayConfig(text_base_url="http://localhost:8080")

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    transcript = await transcribe_audio(audio_bytes, config)
    return {"transcript": transcript}
```

---

## License

MIT License - see [LICENSE](LICENSE) for details
