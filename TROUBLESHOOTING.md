# Troubleshooting

Common issues and solutions for the inference gateway library.

## Server Connection Issues

### "Connection refused" / "Cannot connect to http://localhost:8080"

**Cause:** The inference server is not running or not accessible at the configured URL.

**Solution:**
1. Make sure the server is running:
   ```bash
   # Linux/macOS
   ./scripts/start_server.sh
   
   # Windows
   .\scripts\start_server.ps1
   ```

2. Wait 60+ seconds for the model to fully load
   - You should see `"Ready"` message in the server logs

3. Verify the server is accessible:
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status":"ok"}
   ```

4. Check the port matches your configuration:
   ```python
   config = GatewayConfig(text_base_url="http://localhost:8080")
   ```

5. Check your firewall isn't blocking port 8080

### "Connection timeout" / "Upstream did not respond in time"

**Cause:** Server is running but not responding within the timeout window.

**Solution:**
1. Check if the server is still running (processes can crash)
2. Check server logs for errors
3. Increase timeout in configuration:
   ```python
   config = GatewayConfig(
       text_base_url="http://localhost:8080",
       timeout_s=600.0,  # Increase to 10 minutes
   )
   ```

4. Try a simpler request (check the server is responsive):
   ```bash
   curl http://localhost:8080/v1/models
   ```

---

## Audio Processing Issues

### "audio input is not supported"

**Cause:** The server doesn't have the audio encoder module loaded.

**Solution:**
1. **Use the `-hf` flag** when starting the server (this is critical):
   ```bash
   ./llama-server -hf bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M --port 8080
   ```

2. Don't use these flags (they break audio):
   - `--models-dir` (disables mmproj download)
   - Router mode configurations

3. Wait for "Ready" message before using the library

### Audio file format not supported

**Cause:** The audio format isn't recognized or ffmpeg isn't installed.

**Solution:**
1. Enable audio preprocessing in your config:
   ```python
   config = GatewayConfig(
       text_base_url="http://localhost:8080",
       audio_preprocess_enabled=True,  # Convert to WAV
   )
   ```

2. Ensure ffmpeg is installed:
   ```bash
   # Linux
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/
   # Or use: choco install ffmpeg
   ```

3. Verify ffmpeg is accessible:
   ```bash
   ffmpeg -version
   ```

4. If ffmpeg is in a non-standard location:
   ```python
   config = GatewayConfig(
       text_base_url="http://localhost:8080",
       audio_preprocess_enabled=True,
       ffmpeg_bin="/path/to/ffmpeg",
   )
   ```

### "Audio file too large" or "Max upload bytes exceeded"

**Cause:** Audio file exceeds the configured maximum size.

**Solution:**
Increase the maximum upload size:
```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",
    audio_max_upload_bytes=100_000_000,  # 100 MB instead of 20 MB
)
```

Or compress/split the audio file before processing.

---

## Response Parsing Issues

### "choices field not found in response" / "Invalid response format"

**Cause:** The server returned an error or unexpected response format.

**Solution:**
1. Check server logs for errors
2. Try a simpler request first:
   ```python
   response = await chat_completion(
       messages=[{"role": "user", "content": "Hi"}],
       config=config,
   )
   ```

3. Verify the model loaded successfully:
   ```bash
   curl http://localhost:8080/v1/models
   ```

4. Check if the server returned 500 error:
   ```bash
   # Test the endpoint directly
   curl -X POST http://localhost:8080/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "hi"}]}'
   ```

### "Missing required fields in request"

**Cause:** The request is missing required OpenAI-format fields.

**Solution:**
Ensure messages always follow this format:
```python
messages = [
    {
        "role": "user",  # required: "user", "assistant", or "system"
        "content": "Your message"  # required: string or list of content blocks
    }
]
```

For audio:
```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "input_audio",
                "input_audio": {"data": base64_audio, "format": "wav"}
            }
        ]
    }
]
```

---

## Configuration Issues

### "text_base_url is required" / "Configuration error"

**Cause:** Required configuration is missing.

**Solution:**
Always provide the required configuration:
```python
config = GatewayConfig(
    text_base_url="http://localhost:8080",  # Required
    routing_mode="single",  # Optional, default
)
```

### "Upstream URL is invalid"

**Cause:** The URL format is incorrect.

**Solution:**
Use proper URL format:
```python
# Good
config = GatewayConfig(text_base_url="http://localhost:8080")
config = GatewayConfig(text_base_url="https://api.example.com:8080")

# Bad
config = GatewayConfig(text_base_url="localhost:8080")  # Missing http://
config = GatewayConfig(text_base_url="http://localhost:8080/")  # Trailing slash
```

---

## Performance Issues

### Slow response times

**Causes & Solutions:**

1. **Model is still loading:**
   - Wait 60+ seconds after starting the server
   - Check server logs for "Ready" message

2. **System is CPU-bound:**
   - Reduce concurrent requests
   - Use a faster machine
   - Try a smaller model

3. **Network latency:**
   - Check server is on same network/machine
   - Use localhost instead of IP address
   - Check for network congestion

4. **Upstream timeout too short:**
   ```python
   config = GatewayConfig(
       text_base_url="http://localhost:8080",
       timeout_s=600.0,  # Increase timeout for large requests
   )
   ```

### High memory usage

**Causes & Solutions:**

1. **Large audio files:**
   - Enable preprocessing to normalize file size
   - Split large files into chunks

2. **Too many concurrent requests:**
   - Limit concurrent requests:
     ```python
     semaphore = asyncio.Semaphore(5)
     
     async def limited_transcribe(audio):
         async with semaphore:
             return await transcribe_audio(audio, config)
     ```

3. **Memory leak in your code:**
   - Ensure resources are properly cleaned up
   - Use context managers for file I/O

---

## Common Error Messages

### "AudioProcessingError: ffmpeg not found"

**Solution:** Install ffmpeg (see [Audio file format not supported](#audio-file-format-not-supported))

### "UpstreamUnreachableError: Connection to upstream failed"

**Solution:** Check server is running (see [Connection refused](#connection-refused--cannot-connect-to-httplocalhost8080))

### "UpstreamTimeoutError: Upstream did not respond in time"

**Solution:** Increase timeout or check server (see [Connection timeout](#connection-timeout--upstream-did-not-respond-in-time))

### "ConfigurationError: audio_preprocess_enabled requires ffmpeg"

**Solution:** Install ffmpeg or disable preprocessing

### "InvalidRequestError: Response from upstream was not JSON"

**Solution:** Check server is responding correctly (see [Response Parsing Issues](#response-parsing-issues))

---

## Getting Help

1. **Check the logs:**
   - Server logs for upstream errors
   - Python traceback for library errors

2. **Review examples:**
   - See `examples/` directory for working code

3. **Read the full documentation:**
   - [USAGE_GUIDE.md](USAGE_GUIDE.md) - Complete API reference
   - [ARCHITECTURE.md](ARCHITECTURE.md) - How it works internally

4. **Common scenarios:**
   - [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
   - [USAGE_GUIDE.md#common-patterns](USAGE_GUIDE.md#common-patterns) - Common use cases

5. **Submit an issue:**
   - Check existing issues first
   - Include: error message, Python version, OS, what you were trying to do

---

## System Requirements

- **Python:** 3.11+
- **Server:** llama.cpp with Voxtral model
- **Dependencies:** httpx, pydantic (auto-installed)
- **Optional:** ffmpeg (for audio preprocessing)

## Server Compatibility

This library is designed for:
- **llama.cpp** servers with OpenAI-compatible API
- **Voxtral model** (or other models with audio support)
- Does NOT work with: OpenAI API, vLLM, other non-OpenAI-compatible servers

If you need to use a different server, see [USAGE_GUIDE.md#migration-from-server-mode-v010](USAGE_GUIDE.md#migration-from-server-mode-v010) for options.
