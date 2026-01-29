# Coding AI Examples — Inference Gateway
====================================

This document contains concrete examples that define **HOW** the coding AI is expected to think, structure code, and respect boundaries in this repo.

These examples are **normative**. Follow them exactly.

**Note:** These principles apply to **both** the server mode (v0.1.0) and library mode (v0.2.0).
They focus on architectural philosophy and design patterns that transcend implementation details.

For **library-specific examples**, see [LIBRARY_USAGE.md](LIBRARY_USAGE.md).

Purpose:
- Teach behavior, not just syntax
- Prevent architectural drift
- Reduce “creative” but incorrect implementations

If an implementation conflicts with these examples, **the examples win**.

---

## Example 1 — Correct Responsibility Split (MOST IMPORTANT)

### ❌ Bad (what NOT to do)

```python
# app/main.py

@app.post("/v1/transcribe")
async def transcribe(file: UploadFile):
    audio = await file.read()
    wav = run_ffmpeg(audio)              # ❌ ffmpeg logic here
    payload = build_payload(wav)          # ❌ payload construction here
    async with httpx.AsyncClient() as c:  # ❌ upstream call here
        r = await c.post(...)
    return r.json()
```

### ✅ Good (what TO do)

```python
# app/main.py
@app.post("/v1/transcribe")
async def transcribe(file: UploadFile):
    return await transcribe_endpoint(file)
```

```python
# app/audio.py
def normalize_to_wav(input_bytes: bytes) -> bytes:
    ...
```

```python
# app/forwarder.py
async def forward_chat_completion(payload: dict) -> httpx.Response:
    ...
```

```python
# app/endpoints/transcribe.py (or helper function)
async def transcribe_endpoint(file: UploadFile):
    wav = normalize_to_wav(await file.read())
    payload = build_openai_payload(wav)
    response = await forward_chat_completion(payload)
    return {"transcript": extract_text(response)}
```

**Rule learned by the AI:**  
> Endpoints orchestrate. They never *do* the work.

---

## Example 2 — OpenAI Pass-through Means NO Interpretation

### ❌ Bad

```python
# AI invents new fields
payload["audio"] = wav_bytes
payload["task"] = "transcription"
```

### ✅ Good

```python
payload = {
    "model": model_id,
    "messages": [
        {
            "role": "system",
            "content": "Transkribiere Audio wortgetreu."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64_audio,
                        "format": "wav"
                    }
                }
            ]
        }
    ],
    "temperature": 0
}
```

**Rule learned:**  
> If it is not part of the OpenAI-compatible schema, do not invent it.

---

## Example 3 — Routing Is Structural, Never Semantic

### ❌ Bad

```python
# AI tries to be clever
if "transcribe" in system_prompt.lower():
    backend = AUDIO_BACKEND
```

### ✅ Good

```python
def has_audio(messages: list[dict]) -> bool:
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if part.get("type") in {"input_audio", "audio"}:
                    return True
    return False
```

```python
backend = AUDIO_BASE_URL if has_audio(payload["messages"]) else TEXT_BASE_URL
```

**Rule learned:**  
> Routing decisions are made by JSON structure, not meaning.

---

## Example 4 — ffmpeg Usage Must Be Boring and Deterministic

### ❌ Bad

```python
cmd = f"ffmpeg -i {user_input} -filter_complex some_magic"
```

### ✅ Good

```python
cmd = [
    FFMPEG_BIN,
    "-y",
    "-i", input_path,
    "-ac", "1",
    "-ar", "16000",
    "-f", "wav",
    output_path,
]
```

**Rule learned:**  
> ffmpeg commands are fixed, explicit, and never user-influenced.

---

## Example 5 — Upstream HTTP Calls (Correct vs Incorrect)

### ❌ Bad

```python
import requests
r = requests.post(url, json=payload)
```

### ✅ Good

```python
async with httpx.AsyncClient(timeout=timeout) as client:
    r = await client.post(
        f"{base_url}/v1/chat/completions",
        json=payload,
        headers=headers,
    )
```

**Rule learned:**  
> Async code uses httpx.AsyncClient with explicit timeouts.

---

## Example 6 — Error Handling Philosophy

### ❌ Bad

```python
except Exception:
    return {"error": "something went wrong"}
```

### ✅ Good

```python
except httpx.TimeoutException:
    raise HTTPException(
        status_code=504,
        detail={
            "error": {
                "type": "upstream_timeout",
                "message": "Inference backend did not respond in time"
            }
        }
    )
```

**Rule learned:**  
> Errors are explicit, typed, and mapped to HTTP semantics.

---

## Example 7 — What “Content-Agnostic” Really Means

### ❌ Bad

```python
# AI adds domain logic
if "appointment" in transcript:
    category = "scheduling"
```

### ✅ Good

```python
# Gateway does not classify or interpret meaning
return upstream_response
```

**Rule learned:**  
> The gateway never understands content. It only transports it.

---

## Example 8 — Adding a New Feature (Correct Process)

### ❌ Bad

```text
Just add code wherever it fits.
```

### ✅ Good

```text
Step 1: Identify responsibility
Step 2: Decide which module owns it
Step 3: Propose a new file if responsibility does not fit existing modules
Step 4: Update AGENTS.md if boundaries change
Step 5: Implement minimal version
Step 6: Add or update tests
```

**Rule learned:**  
> Structure decisions precede implementation.

---

## Example 9 — Minimalism Over Cleverness

### ❌ Bad

```python
# AI adds retries, caching, heuristics, fallbacks
```

### ✅ Good

```python
# Single upstream call
# Explicit timeout
# Single responsibility
```

**Rule learned:**  
> Do the simplest thing that is correct and configurable.

---

## Example 10 — The North Star (Memorize This)

> **This repository implements an OpenAI-compatible inference gateway.  
> It normalizes inputs, forwards requests, and returns responses.  
> It does not interpret, classify, optimize, or decide.**
