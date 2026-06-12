#!/usr/bin/env bash
# Gorilla AI - Initial Setup Script
# Configures the environment and downloads required models

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check dependencies
command -v docker >/dev/null 2>&1 || error "Docker is required. Install from https://docs.docker.com/get-docker/"
command -v docker compose >/dev/null 2>&1 || error "Docker Compose V2 is required."

info "Gorilla AI Setup Starting..."

# Create .env if not exists
if [ ! -f .env ]; then
    cat > .env <<EOF
# Gorilla AI Environment Configuration
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
DEFAULT_MODEL=qwen2.5:14b
EMBED_MODEL=BAAI/bge-m3
EMBED_DEVICE=cpu
LOG_LEVEL=INFO
API_URL=http://localhost:8000
WS_URL=ws://localhost:8000
EOF
    info ".env file created"
fi

# Detect GPU
if command -v nvidia-smi >/dev/null 2>&1; then
    info "NVIDIA GPU detected. Using GPU profile."
    COMPOSE_PROFILE="gpu"
else
    warn "No GPU detected. Running in CPU mode (slower)."
    COMPOSE_PROFILE="cpu"
    # Switch to smaller model for CPU
    sed -i 's/DEFAULT_MODEL=qwen2.5:14b/DEFAULT_MODEL=qwen2.5:7b/' .env
fi

# Start infrastructure services
info "Starting infrastructure services..."
docker compose --profile "$COMPOSE_PROFILE" up -d postgres redis qdrant

# Wait for services
info "Waiting for services to be healthy..."
sleep 5

# Start Ollama
info "Starting Ollama..."
docker compose --profile "$COMPOSE_PROFILE" up -d ollama${COMPOSE_PROFILE:+-${COMPOSE_PROFILE}}

# Pull the LLM model
MODEL=$(grep DEFAULT_MODEL .env | cut -d= -f2)
info "Pulling LLM model: $MODEL (this may take a while...)"
docker compose exec ollama-${COMPOSE_PROFILE} ollama pull "$MODEL" || \
docker exec "$(docker compose ps -q ollama-cpu 2>/dev/null || docker compose ps -q ollama)" ollama pull "$MODEL"

# Pull embedding model (via Python)
info "Downloading embedding model (BGE-M3)..."
docker run --rm -v gorilla_model_cache:/root/.cache/huggingface \
    python:3.11-slim \
    python -c "
from huggingface_hub import snapshot_download
snapshot_download('BAAI/bge-m3', cache_dir='/root/.cache/huggingface')
print('BGE-M3 downloaded successfully')
" 2>/dev/null || warn "Could not pre-download embedding model. It will be downloaded on first use."

# Start backend
info "Starting backend..."
docker compose up -d backend

# Start frontend
info "Starting frontend..."
docker compose up -d frontend

info ""
info "======================================"
info " Gorilla AI is ready!"
info "======================================"
info " WebUI:    http://localhost:3000"
info " API:      http://localhost:8000"
info " API Docs: http://localhost:8000/docs"
info " Qdrant:   http://localhost:6333/dashboard"
info "======================================"
