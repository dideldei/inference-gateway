# Server Startup Scripts

Quick scripts to start llama.cpp server with the correct configuration for Inference Gateway.

## Windows (PowerShell)

```powershell
.\start_server.ps1
```

**With custom port:**
```powershell
.\start_server.ps1 -Port 9000
```

**With custom host and port:**
```powershell
.\start_server.ps1 -Port 9000 -Host 0.0.0.0
```

## Linux / macOS

```bash
chmod +x start_server.sh  # Make executable (first time only)
./start_server.sh
```

**With custom port:**
```bash
./start_server.sh 9000
```

**With custom host and port:**
```bash
./start_server.sh 9000 0.0.0.0
```

## What These Scripts Do

1. ✅ Verify `llama-server` is installed
2. ✅ Start server with Voxtral model
3. ✅ Automatically load audio encoder (mmproj)
4. ✅ Listen on configured host:port
5. ✅ Show helpful error messages if something fails

## Requirements

- llama.cpp installed and `llama-server` in PATH
- ~4 GB disk space for model
- GPU recommended (RTX 3060 or better)

## Installation

### Windows
```powershell
choco install llama.cpp
```
Or download from: https://github.com/ggml-org/llama.cpp/releases

### macOS
```bash
brew install llama.cpp
```

### Linux
```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
make
sudo cp ./llama-server /usr/local/bin/
```

## Verify Server is Running

Once started, in another terminal:
```bash
curl http://localhost:8080/health
```

Should return:
```json
{"status":"ok"}
```

## Default Configuration

- **Model**: bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M
- **Host**: 127.0.0.1 (localhost only)
- **Port**: 8080
- **Audio Encoder**: Automatic (via `-hf` flag)

## Using with Inference Gateway

Once server is running, configure your library:

```python
from inference_gateway import GatewayConfig

config = GatewayConfig(text_base_url="http://localhost:8080")
```

Or if using custom port:
```python
config = GatewayConfig(text_base_url="http://localhost:9000")
```

## Troubleshooting

### "llama-server not found"
- Install llama.cpp properly
- Ensure it's in your PATH
- Restart terminal after installation

### "audio input is not supported"
- `-hf` flag automatically loads mmproj
- Make sure you're using the correct model name
- Check server logs for more details

### Server starts but exits immediately
- Check disk space (need ~4 GB)
- Check GPU memory (if using CUDA)
- Check server logs for specific errors

## Environment Variables

You can also set these before running:

```bash
# Linux/macOS
export LLAMA_PORT=9000
export LLAMA_HOST=0.0.0.0

# PowerShell
$env:LLAMA_PORT = "9000"
$env:LLAMA_HOST = "0.0.0.0"
```

## Notes

- First start takes longer (downloads model and mmproj)
- Subsequent starts are faster (uses cache)
- Server listens on localhost (127.0.0.1) by default for security
- Use `0.0.0.0` to allow remote connections (not recommended in production)
