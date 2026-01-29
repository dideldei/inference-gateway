# Inference Gateway Library

Core library code for OpenAI-compatible audio transcription and text generation.

## Module Structure

```
inference_gateway/
├── __init__.py                 # Public API
├── core/
│   ├── audio.py               # Audio preprocessing
│   ├── client.py              # HTTP forwarding
│   ├── config.py              # Configuration
│   ├── exceptions.py          # Custom exceptions
│   ├── operations.py          # High-level API
│   └── routing.py             # Backend routing logic
└── utils/
    └── logging.py             # Logging utilities
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

## Core Modules

- **config.py** - Configuration management (GatewayConfig)
- **operations.py** - High-level async operations (transcribe, analyze, chat)
- **client.py** - Low-level HTTP forwarding to upstream
- **audio.py** - Audio format conversion and preprocessing
- **routing.py** - Logic for selecting upstream server (single vs audio_text mode)
- **exceptions.py** - Custom exception types

## Documentation

Full documentation is in the repository root:

- [QUICKSTART.md](../QUICKSTART.md) - Get started in 5 minutes
- [USAGE_GUIDE.md](../USAGE_GUIDE.md) - Complete API reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Design and internals
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Common issues

## Dependencies

- `httpx>=0.25.0` - Async HTTP client
- `pydantic>=2.0.0` - Data validation

Optional:
- `ffmpeg` - For audio preprocessing (if enabled)

## Testing

Run tests with pytest:

```bash
pytest tests/
```

Integration tests in `tests/integration_test_*.py` require a running inference server.
