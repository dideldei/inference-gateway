#!/usr/bin/env pwsh
<#
.SYNOPSIS
Start llama.cpp server with Voxtral model and audio encoder for Inference Gateway

.DESCRIPTION
Starts llama-server with the correct configuration:
- Model: bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M
- Audio encoder (mmproj): Automatically loaded via -hf flag
- Host: 127.0.0.1
- Port: 8080

.EXAMPLE
.\start_server.ps1

.EXAMPLE
.\start_server.ps1 -Port 9000  # Use custom port
#>

param(
    [int]$Port = 8080,
    [string]$Host = "127.0.0.1"
)

Write-Host "🚀 Starting llama.cpp server for Inference Gateway" -ForegroundColor Green
Write-Host ""

$Model = "bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M"

Write-Host "⚙️  Configuration:" -ForegroundColor Cyan
Write-Host "   Model: $Model"
Write-Host "   Host: $Host"
Write-Host "   Port: $Port"
Write-Host "   Audio Encoder: Automatic (mmproj via -hf)"
Write-Host ""

Write-Host "📍 Starting server..." -ForegroundColor Yellow
Write-Host "   Command: llama-server -hf $Model --host $Host --port $Port"
Write-Host ""

# Check if llama-server is available
$LlamaServerPath = Get-Command llama-server -ErrorAction SilentlyContinue

if (-not $LlamaServerPath) {
    Write-Host "❌ ERROR: llama-server not found in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install llama.cpp first:" -ForegroundColor Yellow
    Write-Host "   https://github.com/ggml-org/llama.cpp/releases"
    Write-Host "   or via Chocolatey: choco install llama.cpp"
    exit 1
}

Write-Host "✅ llama-server found: $($LlamaServerPath.Source)" -ForegroundColor Green
Write-Host ""

# Start server
Write-Host "Starting server... (this may take 30-60 seconds to load the model)" -ForegroundColor Cyan
Write-Host ""

try {
    & llama-server -hf $Model --host $Host --port $Port
}
catch {
    Write-Host "❌ ERROR: Failed to start server" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
