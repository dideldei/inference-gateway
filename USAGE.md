# Inference Gateway Library - Usage Guide

A lightweight Python library for audio transcription and text generation using OpenAI-compatible APIs.

## Installation

```bash
pip install inference-gateway
```

## Quick Start

### 1. Start the Server

```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

### 2. Use the Library

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio, analyze_audio, chat_completion

# Configure
config = GatewayConfig(text_base_url="http://localhost:8080")

# Transcribe audio
async def transcribe():
    with open("audio.wav", "rb") as f:
        transcript = await transcribe_audio(f.read(), config)
    return transcript

# Analyze audio
async def analyze():
    with open("audio.wav", "rb") as f:
        analysis = await analyze_audio(
            f.read(),
            instruction="Summarize this conversation",
            config=config,
        )
    return analysis

# Text completion
async def chat():
    response = await chat_completion(
        messages=[
            {"role": "user", "content": "What is AI?"}
        ],
        config=config,
    )
    return response["choices"][0]["message"]["content"]

# Run
result = asyncio.run(transcribe())
```

## API Reference

### GatewayConfig

```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",  # Required: Server URL
    routing_mode="single",                   # Single backend
    timeout_s=300.0,                         # Request timeout
    connect_timeout_s=10.0,                  # Connection timeout
    audio_preprocess_enabled=False,          # Auto normalize audio (requires ffmpeg)
)
```

### transcribe_audio()

Transcribe audio file to text.

```python
transcript = await transcribe_audio(audio_bytes, config)
```

**Parameters:**
- `audio_bytes: bytes` - Audio file as bytes
- `config: GatewayConfig` - Configuration
- `system_prompt: str | None` - Optional custom system prompt

**Returns:** `str` - Transcribed text

---

### analyze_audio()

Analyze audio with custom instruction.

```python
result = await analyze_audio(
    audio_bytes,
    instruction="Summarize the main points",
    config=config,
)
```

**Parameters:**
- `audio_bytes: bytes` - Audio file as bytes
- `instruction: str` - What to analyze
- `config: GatewayConfig` - Configuration
- `system_prompt_prefix: str | None` - Optional system prompt prefix

**Returns:** `str` - Analysis result

---

### chat_completion()

Send chat message and get response (OpenAI-compatible).

```python
response = await chat_completion(
    messages=[
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ],
    config=config,
    temperature=0.7,
    max_tokens=100,
)

text = response["choices"][0]["message"]["content"]
```

**Parameters:**
- `messages: list[dict]` - OpenAI format messages
- `config: GatewayConfig` - Configuration
- `**openai_params` - Additional params (temperature, max_tokens, etc.)

**Returns:** `dict` - OpenAI-compatible response

---

## Common Patterns

### Batch Processing (Concurrent)

```python
async def process_files(audio_files: list) -> dict:
    config = GatewayConfig(text_base_url="http://localhost:8080")
    
    async def process_one(audio_file):
        with open(audio_file, "rb") as f:
            return audio_file, await transcribe_audio(f.read(), config)
    
    tasks = [process_one(f) for f in audio_files]
    return dict(await asyncio.gather(*tasks))

result = asyncio.run(process_files(["audio1.wav", "audio2.wav"]))
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
```

---

## Server Setup

### Start Server (with Audio Encoder)

```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

**Important:** The `-hf` flag automatically downloads and loads the mmproj (audio encoder) which is **required** for audio transcription and analysis.

Without the `-hf` flag and mmproj, you'll get: `"audio input is not supported"`

### Verify Server

```bash
curl http://localhost:8080/health
# Returns: {"status":"ok"}
```

---

## Testing

Run included test scripts:

```bash
# Test transcription and analysis
python test_transcribe_wav.py
python test_analyze_wav.py
python test_wav_complete.py
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

## Troubleshooting

### "Connection refused"
- Verify llama-server is running
- Check port in GatewayConfig matches server
- Wait 60+ seconds for model to load

### "audio input is not supported"
- Use `-hf` flag when starting server
- Do NOT use `--models-dir` or router mode

### "choices field not found"
- Server returned 500 error
- Check server logs for specific error
- Verify model loaded successfully

---

## Performance

- **Transcription:** ~5-10 seconds per minute of audio
- **Analysis:** ~3-5 seconds
- **Batch processing:** Use `asyncio.gather()` for parallel processing
- **Concurrent requests:** Server supports multiple parallel requests

---

## Dependencies

- `httpx>=0.25.0` - Async HTTP client
- `pydantic>=2.0.0` - Data validation

Optional:
- `ffmpeg` - For audio preprocessing (if enabled)

---

## License

[Add your license]
