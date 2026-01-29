# ⚠️ ARCHIVE — v0.1.0 (Server Mode)

This document describes implementation tickets for the original server mode (v0.1.0).

**For the current library mode (v0.2.0):**
- See [LIBRARY_USAGE.md](LIBRARY_USAGE.md) for complete API documentation
- See [examples/](examples/) for working code examples
- See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for transition details

**This is kept for historical reference.**

---

## Archived Tickets (v0.1.0)

### Project Goal
Build a standalone, reusable **Inference Gateway** that provides a stable HTTP interface for LLM inference.  
The gateway is **content-agnostic**: it forwards OpenAI-compatible requests to one or more upstream backends (e.g., local inference servers).  
Optionally, it can **preprocess audio uploads** (normalize with ffmpeg and inject into an OpenAI chat payload).

The gateway must support:
- Local development (single machine) and later deployment on a server/LXC
- Seamless migration via environment configuration (no code changes)
- Deterministic and testable behavior
- Minimal scope: proxy + preprocessing + routing; no business logic

---

## Key Principles
1) **OpenAI-compatible API** as the primary contract (pass-through).
2) **Gateway is thin**: it does not interpret content or implement domain workflows.
3) **Routing is configuration-driven**, based on request characteristics (e.g., contains audio).
4) **Audio preprocessing is optional** and strictly controlled by config.
5) **Operational usability**: health checks, logging, timeouts, safe defaults.

---

## Public API (Gateway)
### Required
- `GET /health` → `{ "ok": true, "version": "...", "upstreams": {...} }`
- `POST /v1/chat/completions` → forwards OpenAI-compatible chat requests
- `GET /v1/models` → forwards model listing (if upstream supports it)

### Optional Convenience Endpoints (thin wrappers)
- `POST /v1/transcribe` (multipart audio file) → returns `{ "transcript": "..." }`
- `POST /v1/analyze` (multipart audio file + instruction) → returns `{ "result": "..." }`

Convenience endpoints must be implemented **by constructing** an OpenAI-compatible chat request internally and calling the same forwarding pipeline used by `/v1/chat/completions`.

---

## Upstream Compatibility Assumption
Upstreams are expected to provide OpenAI-like endpoints:
- `/v1/chat/completions`
- `/v1/models` (optional but recommended)

If a given upstream lacks `/v1/models`, the gateway should degrade gracefully:
- `/v1/models` returns 502 with a clear message OR offers an aggregate list from configured static model IDs.

---

## Ticket List

### T0 — Repository Bootstrap
**Deliverables**
- New git repo: `inference-gateway`
- Python project with `pyproject.toml`
- Directory structure:
   
inference-gateway/
├─ app/
│  ├─ main.py                # FastAPI app & router registration
│  ├─ config.py              # ENV → typed settings (pydantic)
│  ├─ routing.py             # Backend routing logic (audio vs text)
│  ├─ forwarder.py           # OpenAI-compatible request forwarding
│  ├─ audio.py               # ffmpeg normalization utilities
│  ├─ schemas.py             # Minimal response/request schemas
│  ├─ security.py            # API key auth, request limits
│  ├─ logging.py             # structured logging setup
│  └─ __init__.py
│
├─ scripts/
│  ├─ dev_run.sh             # start gateway locally
│  ├─ healthcheck.sh         # curl-based health checks
│  └─ lint.sh                # optional
│
├─ tests/
│  ├─ test_health.py
│  ├─ test_routing.py
│  ├─ test_forwarder.py
│  └─ __init__.py
│
├─ deploy/
│  ├─ systemd/
│  │  └─ inference-gateway.service
│  └─ DEPLOYMENT_NOTES.md
│
├─ .env.example
├─ pyproject.toml
├─ README.md
└─ AGENTS.md



**Acceptance**
- `python -m venv .venv && pip install -e .` works
- `uvicorn app.main:app` starts
- `GET /health` returns 200

---

### T1 — Configuration System (Typed + Complete)
**Description**
- Implement `app/config.py` that loads environment variables into a typed settings object.
- Ensure **every behavior** is controllable by config; avoid hidden defaults.

**Required ENV**
- Gateway server:
  - `GATEWAY_HOST` (default `127.0.0.1`)
  - `GATEWAY_PORT` (default `8090`)
- Upstreams:
  - `TEXT_BASE_URL` (e.g., `http://127.0.0.1:11434` or `http://...:8080`)
  - `AUDIO_BASE_URL` (e.g., `http://...:8080`)
  - `DEFAULT_BASE_URL` (optional; if empty, use TEXT_BASE_URL)
- Routing:
  - `ROUTING_MODE` ∈ `{single, audio_text}`  
    - `single`: all requests go to `DEFAULT_BASE_URL` (or TEXT_BASE_URL)
    - `audio_text`: requests containing audio go to AUDIO_BASE_URL; others to TEXT_BASE_URL
- Timeouts:
  - `UPSTREAM_TIMEOUT_S` (default 300)
  - `UPSTREAM_CONNECT_TIMEOUT_S` (default 10)
- Security (gateway-level):
  - `API_KEY` (optional; if set, require `Authorization: Bearer <API_KEY>`)
  - `ALLOW_ORIGINS` (optional CORS list; default empty)
- Audio preprocessing:
  - `FFMPEG_BIN` (default `ffmpeg`)
  - `AUDIO_PREPROCESS_ENABLED` (default `1`)
  - `AUDIO_TARGET_SR` (default `16000`)
  - `AUDIO_TARGET_CHANNELS` (default `1`)
  - `AUDIO_LOUDNORM` (default `1`)
  - `AUDIO_LOUDNORM_FILTER` (default `loudnorm=I=-16:TP=-1.5:LRA=11`)
- Convenience prompts:
  - `TRANSCRIBE_SYSTEM_PROMPT`
  - `ANALYZE_SYSTEM_PROMPT_PREFIX` (optional preface; can be empty)
- Logging:
  - `LOG_LEVEL` (default `INFO`)
  - `LOG_REQUEST_BODIES` (default `0`)

**Acceptance**
- `.env.example` includes all settings with comments
- Settings validate at startup; missing required upstream URLs cause a clear error in logs

---

### T2 — Core Forwarding Pipeline (OpenAI Pass-through)
**Description**
- Implement `POST /v1/chat/completions` as a proxy endpoint:
  - read incoming JSON body
  - validate minimally (must be JSON object)
  - select upstream base URL via routing rules
  - forward request to upstream `/v1/chat/completions` using `httpx`
  - stream response? (optional; define later)
  - return upstream response body + status code transparently
- Implement `GET /v1/models` similarly:
  - forward to chosen upstream
  - in `audio_text` routing mode: optional aggregator behavior:
    - if TEXT and AUDIO upstream differ, return merged list with provenance field (optional)
    - keep it simple: default route `/v1/models` to TEXT upstream unless configured otherwise

**Error Handling**
- Upstream connection failure → 502 with structured error JSON:
  - `{ "error": { "type": "upstream_unreachable", "message": "...", "upstream": "..." } }`
- Upstream timeout → 504 with structured error JSON
- Upstream non-JSON body → pass-through as-is (do not force JSON)

**Acceptance**
- Requests pass through unchanged (except headers the gateway controls)
- Status codes match upstream where possible
- Gateway never hangs indefinitely (timeouts enforced)

---

### T3 — Routing Rules (Content-aware, but minimal)
**Description**
Implement routing selection function:
- If `ROUTING_MODE=single`: always use DEFAULT/TEXT base URL
- If `ROUTING_MODE=audio_text`:
  - detect “audio present” in OpenAI chat payload:
    - `messages[*].content` can be:
      - string (text-only)
      - array of typed parts (OpenAI style). If any part has:
        - `type == "input_audio"` OR `type == "audio"` (support both, configurable)  
          → route to AUDIO_BASE_URL
  - otherwise route to TEXT_BASE_URL
- For robustness, also detect audio in convenience endpoints (always AUDIO_BASE_URL)

**Acceptance**
- Unit tests for routing detection (text-only vs audio content array)
- No domain-specific classification; only structural inspection

---

### T4 — Audio Preprocessing Module (ffmpeg)
**Description**
- Create `app/audio.py`:
  - normalize input bytes/file to WAV PCM mono 16kHz (configurable)
  - optional loudnorm filter (configurable)
  - strict cleanup of temp files
  - bound max upload size (configurable) to prevent abuse
- Add MIME/extension tolerance: accept any audio input; rely on ffmpeg

**Acceptance**
- Given an mp3/wav/m4a fixture, normalization creates a valid wav
- ffmpeg errors are captured and returned as 400 with actionable message

---

### T5 — Convenience Endpoint: `/v1/transcribe`
**Description**
- Input: multipart `file`
- Behavior:
  - if `AUDIO_PREPROCESS_ENABLED=1`, normalize with ffmpeg; else accept wav as-is (document requirement)
  - build OpenAI chat payload:
    - `system` prompt from `TRANSCRIBE_SYSTEM_PROMPT`
    - `user` content includes audio part `{type: input_audio, ...}`
  - forward through the same internal pipeline used by `/v1/chat/completions`
  - parse upstream response and return:
    - `{ "transcript": "<assistant content>" }`

**Acceptance**
- For a short test audio, returns JSON with `transcript` string
- If upstream returns invalid structure, gateway returns 502 with clear message

---

### T6 — Convenience Endpoint: `/v1/analyze`
**Description**
- Input: multipart `file` + form field `instruction` (string)
- Behavior:
  - normalize audio (if enabled)
  - compose prompt:
    - system prompt = `ANALYZE_SYSTEM_PROMPT_PREFIX` (optional) + instruction
  - build OpenAI payload with audio in user content
  - forward to upstream and return `{ "result": "<assistant content>" }`

**Acceptance**
- Works similarly to `/v1/transcribe`
- Instruction is passed verbatim; gateway does not interpret it

---

### T7 — Security & Operational Controls
**Description**
- Optional API key enforcement:
  - If `API_KEY` is set, require `Authorization: Bearer <API_KEY>` for all endpoints except `/health`
- CORS:
  - configurable allowlist
- Request limits:
  - max upload bytes for audio endpoints (config)
  - max JSON body size (optional; at least document expectation)
- Logging:
  - structured logs with request ID
  - never log raw audio or secrets
  - optional `LOG_REQUEST_BODIES=1` for dev only (warn in README)

**Acceptance**
- With API_KEY set, requests without auth return 401
- `/health` remains accessible without auth (configurable if desired)

---

### T8 — Smoke Tests + Local Developer Experience
**Description**
- `tests/test_health.py`: `/health` returns ok
- `tests/test_routing.py`: routing selection works
- `tests/test_transcribe_contract.py`: when upstream is mocked, endpoint returns correct JSON shape
- Add `scripts/dev_run.sh`:
  - runs gateway with `.env`
- Add `scripts/healthcheck.sh`:
  - checks `/health`
  - checks upstream reachability if configured

**Acceptance**
- `pytest -q` passes without requiring a real upstream (use mocking)
- Healthcheck script returns non-zero on failures

---

### T9 — Deployment Assets (Preparation, not mandatory for local dev)
**Description**
- Provide `deploy/systemd/inference-gateway.service` (example)
- Provide `deploy/DEPLOYMENT_NOTES.md`:
  - recommended ports
  - firewall guidance (“allow only callers”)
  - recommended memory/timeout defaults
  - upstream separation patterns

**Acceptance**
- Docs are sufficient for a third party to deploy on a Linux box without reading code

---

### T10 — Optional: Streaming Support (Future)
**Description**
- Add `stream=true` support for `/v1/chat/completions`:
  - if request sets `"stream": true`, forward with streaming and return SSE as-is
- This is optional and can be deferred.

**Acceptance**
- Streaming works end-to-end when upstream supports it

---
