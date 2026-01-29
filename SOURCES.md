https://platform.openai.com/docs/api-reference/chat

https://github.com/ggml-org/llama.cpp/blob/master/README.md

https://www.python-httpx.org/async/

https://www.python-httpx.org/advanced/timeouts/

# ffmpeg Mini-Snippet — Audio Normalization for Inference Gateways

## Purpose
Normalize arbitrary user-provided audio into a **deterministic, model-friendly format**  
before forwarding it to an inference backend (e.g. OpenAI-compatible LLM servers).

This snippet intentionally covers **only** what is required.
Do NOT infer additional ffmpeg features beyond this document.

---

## Target Audio Format (Hard Requirement)
- Container: **WAV**
- Codec: **PCM (uncompressed)**
- Sample rate: **16 kHz**
- Channels: **mono (1)**
- Loudness: **optional EBU R128 normalization**

Rationale:
- Widely supported
- Stable for speech models
- Predictable size and duration
- Avoids codec-dependent behavior

---

## Canonical ffmpeg Command (Minimal)

```bash
ffmpeg -y \
  -i INPUT_AUDIO \
  -ac 1 \
  -ar 16000 \
  -f wav \
  OUTPUT.wav




