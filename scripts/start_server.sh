#!/bin/bash
# Start llama.cpp server with Voxtral model and audio encoder for Inference Gateway
#
# Usage:
#   ./start_server.sh              # Use default port 8080
#   ./start_server.sh 9000         # Use custom port
#   ./start_server.sh 9000 0.0.0.0 # Custom port and host

set -e

# Configuration
MODEL="bartowski/mistralai_Voxtral-Mini-3B-2507-GGUF:Q5_K_M"
PORT="${1:-8080}"
HOST="${2:-127.0.0.1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}🚀 Starting llama.cpp server for Inference Gateway${NC}"
echo ""

# Print configuration
echo -e "${CYAN}⚙️  Configuration:${NC}"
echo "   Model: $MODEL"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Audio Encoder: Automatic (mmproj via -hf)"
echo ""

# Check if llama-server is available
if ! command -v llama-server &> /dev/null; then
    echo -e "${RED}❌ ERROR: llama-server not found in PATH${NC}"
    echo ""
    echo -e "${YELLOW}Please install llama.cpp first:${NC}"
    echo "   https://github.com/ggml-org/llama.cpp/releases"
    echo ""
    echo -e "${YELLOW}On macOS with Homebrew:${NC}"
    echo "   brew install llama.cpp"
    echo ""
    echo -e "${YELLOW}On Linux (build from source):${NC}"
    echo "   git clone https://github.com/ggml-org/llama.cpp.git"
    echo "   cd llama.cpp && make"
    exit 1
fi

# Print where llama-server is
LLAMA_PATH=$(which llama-server)
echo -e "${GREEN}✅ llama-server found: $LLAMA_PATH${NC}"
echo ""

# Start server
echo -e "${CYAN}Starting server... (this may take 30-60 seconds to load the model)${NC}"
echo -e "${CYAN}Command: llama-server -hf $MODEL --host $HOST --port $PORT${NC}"
echo ""

# Run server
exec llama-server -hf "$MODEL" --host "$HOST" --port "$PORT"
