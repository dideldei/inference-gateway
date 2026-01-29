# AGENTS.md — Inference Gateway Library (v0.2.0)

## Role

You are implementing a Python **inference gateway library** that provides async functions for interacting with OpenAI-compatible inference backends, with support for audio preprocessing, intelligent routing, and high-level operations.

## Mission

Deliver a small, reliable library that:
- Provides async functions for common inference tasks (transcription, analysis, completion)
- Supports optional audio preprocessing with ffmpeg
- Routes requests intelligently based on configuration and content
- Offers a clean, minimal Python API
- Has minimal dependencies (httpx + pydantic only)

## What This Is

✅ A **Python library** - Functions you import and call  
✅ **Async throughout** - Uses async/await  
✅ **Framework-agnostic** - Works with any Python framework or script  
✅ **Reusable** - Integrate into any Python project  

## What This Is NOT

❌ Not a web server (that's v0.1.0)  
❌ Not FastAPI or HTTP layer  
❌ Not environment-driven configuration (uses GatewayConfig dataclass)  
❌ Not a domain-specific tool (generic forwarding only)  

## Non-Goals

- No persistent storage
- No user management
- No UI
- No domain logic (the library doesn't interpret content)
- No FastAPI/HTTP concerns

## Primary Public API

Users should be able to do this:

```python
from inference_gateway import GatewayConfig, transcribe_audio, analyze_audio

config = GatewayConfig(text_base_url="http://localhost:8080")
transcript = await transcribe_audio(audio_bytes, config)
result = await analyze_audio(audio_bytes, instruction, config)
```

## Code Organization

The library is organized into focused modules:

- **core/config.py** - GatewayConfig dataclass
- **core/operations.py** - High-level async functions
- **core/audio.py** - Audio preprocessing with ffmpeg
- **core/routing.py** - Routing logic (audio vs text detection)
- **core/client.py** - HTTP forwarding to upstream
- **core/exceptions.py** - Custom exception types
- **core/logging.py** - Logging utilities

## Code Standards

- **Python 3.11+** - Modern Python syntax
- **async/await throughout** - All I/O is async
- **httpx** - Async HTTP client (never blocking)
- **pydantic** - Data validation (for GatewayConfig)
- **Minimal dependencies** - Only what's necessary
- **Explicit error handling** - Custom exception types
- **Structured logging** - Using Python logging

## Testing Requirements

- Tests run with **mocked upstream** (use httpx mocking)
- No actual upstream server needed
- Test all core operations
- Test routing logic
- Test error handling

## Definition of Done (v0.2.0)

✅ Library installs: `pip install inference-gateway`  
✅ Core functions are importable and callable  
✅ Examples run without modification  
✅ All tests pass with mocked upstream  
✅ No dependencies on FastAPI  
✅ Documentation is complete  

## Related Files

- [LIBRARY_USAGE.md](LIBRARY_USAGE.md) - API reference and examples
- [EXAMPLES.md](EXAMPLES.md) - Architectural principles
- [examples/](examples/) - Working code examples
- [app/](app/) - Original v0.1.0 server code

---

**Remember**: This is a library, not a service. Think in terms of functions and modules, 
not endpoints and middleware.
