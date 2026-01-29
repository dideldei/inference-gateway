# Quick Start - Get Started in 5 Minutes

Get the inference gateway library running in just a few steps.

## 1. Install (1 minute)

Clone and install from source:

```bash
git clone https://github.com/dideldei/inference-gateway.git
cd inference-gateway
pip install -e .
```

Or if you have it in a local directory:

```bash
pip install -e /path/to/inference-gateway
```

## 2. Start the Server (1 minute)

In one terminal, start the llama.cpp inference server:

**Windows (PowerShell):**
```powershell
.\scripts\start_server.ps1
```

**Linux / macOS:**
```bash
./scripts/start_server.sh
```

Or manually:
```bash
./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
```

Wait for it to load (you'll see "Ready"). Takes ~60 seconds.

## 3. Your First Chat (1 minute)

Create `chat.py`:

```python
import asyncio
from inference_gateway import GatewayConfig, chat_completion

async def main():
    config = GatewayConfig(text_base_url="http://localhost:8080")
    
    response = await chat_completion(
        messages=[{"role": "user", "content": "What is AI?"}],
        config=config,
    )
    
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

Run it:
```bash
python chat.py
```

## 4. Transcribe Audio (1 minute)

Create `transcribe.py`:

```python
import asyncio
from inference_gateway import GatewayConfig, transcribe_audio

async def main():
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        audio_preprocess_enabled=True,  # Handles MP3, WAV, M4A, etc.
    )
    
    with open("audio.wav", "rb") as f:
        transcript = await transcribe_audio(f.read(), config)
    
    print(f"Transcript: {transcript}")

asyncio.run(main())
```

Run it (with your audio file):
```bash
python transcribe.py
```

## 5. Next Steps

- **Full documentation:** See [USAGE_GUIDE.md](USAGE_GUIDE.md)
- **Learn architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Troubleshoot issues:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **See more examples:** Check the `examples/` directory

## What's Next?

You're ready to use the library! Here are some common next steps:

- **Integrate with FastAPI:** See [USAGE_GUIDE.md#fastapi-integration](USAGE_GUIDE.md#fastapi-integration)
- **Process multiple files:** See [USAGE_GUIDE.md#batch-processing-concurrent](USAGE_GUIDE.md#batch-processing-concurrent)
- **Handle errors:** See [USAGE_GUIDE.md#error-handling](USAGE_GUIDE.md#error-handling)
- **Configure timeouts:** See [USAGE_GUIDE.md#custom-timeout-configuration](USAGE_GUIDE.md#custom-timeout-configuration)

## Troubleshooting

**"Connection refused"?**
- Make sure the server is running (you should see "Ready" message)
- Wait 60+ seconds for model to fully load

**"audio input is not supported"?**
- Make sure you used the `-hf` flag when starting the server
- The audio encoder (mmproj) must be loaded

**"No such file or directory: audio.wav"?**
- Use an actual audio file path
- Or use the test files in `tests/fixtures/`

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help.
