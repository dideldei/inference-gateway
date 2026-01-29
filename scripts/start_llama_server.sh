#!/bin/bash
# Script to start llama.cpp server in standard mode
# Usage: ./start_llama_server.sh

set -e

echo "🚀 Starting llama.cpp Server (Standard Mode)"
echo ""

# Find model path
OLLAMA_MODELS_DIR="$HOME/.ollama/models/blobs"

if [ ! -d "$OLLAMA_MODELS_DIR" ]; then
    echo "❌ Ollama models directory not found: $OLLAMA_MODELS_DIR"
    echo "Please install Ollama and pull a model first:"
    echo "  ollama pull mistralai/Voxtral-Mini-3B-2507-GGUF"
    exit 1
fi

echo "📍 Checking for models..."

# Find first .gguf file
MODEL_PATH=$(find "$OLLAMA_MODELS_DIR" -name "*.gguf" -type f | head -1)

if [ -z "$MODEL_PATH" ]; then
    echo "❌ No .gguf files found in $OLLAMA_MODELS_DIR"
    echo "Please pull a model with Ollama first:"
    echo "  ollama pull mistralai/Voxtral-Mini-3B-2507-GGUF"
    exit 1
fi

echo "✓ Found model: $(basename $MODEL_PATH)"
echo ""

echo "⚙️  Server configuration:"
echo "   Model: $MODEL_PATH"
echo "   Host: 127.0.0.1"
echo "   Port: 8080"
echo "   Mode: Standard (NOT Router Mode)"
echo ""

echo "Starting server..."
echo ""

# Start server in standard mode (not router mode)
llama-server -m "$MODEL_PATH" --host 127.0.0.1 --port 8080 --alias "mistral"
