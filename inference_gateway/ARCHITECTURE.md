# Architecture - Inference Gateway

## Overview

A pure async Python library for audio transcription and text generation using OpenAI-compatible APIs.

## Design Principles

1. **Framework-agnostic** - No FastAPI, Flask, or other web framework dependencies
2. **Async-first** - All I/O operations use async/await
3. **Minimal dependencies** - Only httpx + pydantic
4. **Single responsibility** - Each module has one clear purpose
5. **OpenAI compatible** - Uses standard OpenAI message format

## Module Structure

```
core/
├── config.py        → GatewayConfig (configuration)
├── operations.py    → Public API (transcribe, analyze, chat)
├── client.py        → HTTP layer (upstream forwarding)
├── audio.py         → Audio processing (normalization)
├── routing.py       → Backend selection logic
└── exceptions.py    → Custom exceptions
```

## Data Flow

### Transcription Flow

```
User Code
    ↓
transcribe_audio() [operations.py]
    ↓
normalize_audio_to_wav() [audio.py]  (optional preprocessing)
    ↓
Base64 encode audio
    ↓
Build OpenAI-compatible message:
  {
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": [{"type": "input_audio", "input_audio": {...}}]}
    ]
  }
    ↓
select_upstream_url() [routing.py]  (choose backend)
    ↓
forward_chat_completion() [client.py]  (send HTTP request)
    ↓
Parse response → extract text
    ↓
Return transcript (str)
```

### Chat Completion Flow

```
User Code
    ↓
chat_completion() [operations.py]
    ↓
select_upstream_url() [routing.py]
    ↓
forward_chat_completion() [client.py]
    ↓
Parse JSON response
    ↓
Return dict (OpenAI format)
```

## Key Components

### config.py - Configuration

Defines `GatewayConfig` dataclass with:
- Server URL(s)
- Routing mode (single or audio_text)
- Timeout settings
- Audio preprocessing settings
- System prompts for operations

**Why dataclass?** Simple, immutable, easy to pass around

### operations.py - High-Level API

Public async functions:
- `transcribe_audio(audio_bytes, config)` → str
- `analyze_audio(audio_bytes, instruction, config)` → str
- `chat_completion(messages, config, **params)` → dict
- `list_models(config)` → dict

**Responsibilities:**
1. Validate inputs
2. Preprocess data (audio normalization)
3. Build request payloads
4. Call forwarding layer
5. Parse responses
6. Handle errors

### client.py - HTTP Layer

Low-level async HTTP functions:
- `forward_chat_completion(request_body, base_url, config)` → httpx.Response
- `forward_models(base_url, config)` → httpx.Response

**Responsibilities:**
1. Manage HTTP connections
2. Handle timeouts
3. Convert httpx errors to library exceptions
4. Pass through raw responses (no parsing)

### audio.py - Audio Processing

Audio utilities:
- `normalize_audio_to_wav(audio_bytes, config)` → bytes

**Handles:**
- Format detection (WAV, MP3, OGG, etc.)
- Sample rate conversion
- Channel conversion (mono/stereo)
- Requires ffmpeg if preprocessing enabled

### routing.py - Backend Selection

Logic for choosing upstream server:
- `select_upstream_url(request_body, config)` → str (base_url)

**Modes:**
- `"single"` - Always use text_base_url
- `"audio_text"` - Use audio_base_url for audio, text_base_url for text

### exceptions.py - Error Handling

Custom exception hierarchy:

```
GatewayError (base)
├── AudioProcessingError
├── ConfigurationError
├── InvalidRequestError
└── UpstreamError
    ├── UpstreamUnreachableError
    └── UpstreamTimeoutError
```

## Request/Response Format

### OpenAI-Compatible Messages

All requests use OpenAI format:

```python
{
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "model": "mistral",
    "temperature": 0.7,
    # ... other params
}
```

### Audio Content (input_audio)

For audio operations, user message contains:

```python
{
    "role": "user",
    "content": [
        {
            "type": "input_audio",
            "input_audio": {
                "data": "base64_encoded_audio",
                "format": "wav"
            }
        }
    ]
}
```

### Response Format

All responses are OpenAI-compatible:

```python
{
    "id": "...",
    "object": "text_completion",
    "created": 1234567890,
    "model": "mistral",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The response text"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
}
```

## Async Pattern

All I/O operations are async:

```python
# DON'T do this:
transcript = transcribe_audio(audio_bytes, config)  # ❌ Will error

# DO this:
transcript = await transcribe_audio(audio_bytes, config)  # ✅ Correct

# At top level:
result = asyncio.run(transcribe_audio(audio_bytes, config))
```

## Error Handling Strategy

1. **Input validation** in operations.py
2. **HTTP errors** caught in client.py → converted to library exceptions
3. **Response parsing errors** caught in operations.py
4. **User code** catches specific exceptions (UpstreamUnreachableError, etc.)

```python
try:
    result = await transcribe_audio(audio_bytes, config)
except UpstreamUnreachableError:
    print("Server not running")
except UpstreamTimeoutError:
    print("Server timeout")
except Exception as e:
    print(f"Other error: {e}")
```

## Why No FastAPI Here?

The library is deliberately framework-agnostic because:

1. **Reusability** - Works with FastAPI, Flask, async tasks, notebooks, CLI, etc.
2. **Simplicity** - Fewer dependencies, smaller footprint
3. **Testing** - Can test without starting a web server
4. **Composability** - Can build different interfaces on top (if needed)

If you need HTTP API:
```python
from fastapi import FastAPI, UploadFile
from inference_gateway import GatewayConfig, transcribe_audio

app = FastAPI()
config = GatewayConfig(text_base_url="http://localhost:8080")

@app.post("/transcribe")
async def api_transcribe(file: UploadFile):
    content = await file.read()
    return await transcribe_audio(content, config)
```

## Extension Points

### 1. Add New Operations

Add to operations.py:
```python
async def my_operation(audio_bytes, instruction, config):
    # Build request
    request_body = {...}
    # Forward
    response = await forward_chat_completion(request_body, base_url, config)
    # Parse
    return response.json()[...]
```

### 2. Custom Error Handling

Subclass GatewayError:
```python
from inference_gateway.core.exceptions import GatewayError

class MyError(GatewayError):
    pass
```

### 3. Different Audio Format Support

Extend audio.py:
```python
async def normalize_audio_to_wav(audio_bytes, config):
    # Add custom format handling
    ...
```

## Testing Approach

- **Unit tests** - Test individual functions with mocks
- **Integration tests** - Test with real llama.cpp server
- **Fixtures** - Sample audio files in tests/fixtures/

## Performance Considerations

1. **Async I/O** - Non-blocking network calls
2. **Connection pooling** - httpx reuses connections
3. **Batch processing** - Use asyncio.gather() for multiple files:
   ```python
   results = await asyncio.gather(
       transcribe_audio(f1, config),
       transcribe_audio(f2, config),
       transcribe_audio(f3, config),
   )
   ```

4. **Caching** - Library doesn't cache, but applications can layer caching on top

## Dependencies Rationale

### httpx
- Async HTTP client
- No sync version needed
- Better than aiohttp (more maintained)
- OpenAI uses it

### pydantic
- Data validation
- Type hints integration
- Excellent error messages
- Industry standard

### Optional: ffmpeg
- Audio format conversion
- Only needed if audio_preprocess_enabled=True
- Most modern audio is already WAV, so optional

## Version Compatibility

- Python 3.11+ (uses async, type hints)
- httpx 0.25.0+ (tested with latest)
- pydantic 2.0+ (v1 may work but untested)
