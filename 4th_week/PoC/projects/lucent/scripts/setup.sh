#!/usr/bin/env bash
# One-time (idempotent) setup: checks Docker, picks a free port, builds the
# image, starts the container, and waits for it to report healthy.
# Safe to re-run — it reuses your previous port and the existing build cache.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== Lucent setup ==="

command -v docker >/dev/null 2>&1 || {
  echo "Docker is required. Install Docker Desktop first: https://www.docker.com/products/docker-desktop/"
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "Docker Compose v2 is required (bundled with recent Docker Desktop)."
  exit 1
}

# shellcheck source=./find_free_port.sh
source scripts/find_free_port.sh

if [ -f .env ]; then
  echo "Using existing .env"
else
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [ -f .port ] && APP_PORT=$(cat .port) && is_port_free "$APP_PORT"; then
  echo "Reusing previously selected port: $APP_PORT"
else
  APP_PORT=$(find_free_port 8750)
  echo "Selected free port: $APP_PORT"
fi
echo "$APP_PORT" >.port

if grep -q '^APP_PORT=' .env; then
  sed -i.bak "s/^APP_PORT=.*/APP_PORT=$APP_PORT/" .env && rm -f .env.bak
else
  echo "APP_PORT=$APP_PORT" >>.env
fi

export TORCH_INDEX="https://download.pytorch.org/whl/cpu"
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "NVIDIA GPU detected on this host -> building with the CUDA-enabled torch wheel."
  export TORCH_INDEX="https://download.pytorch.org/whl/cu121"
else
  echo "No NVIDIA GPU detected -> building with the CPU-only torch wheel (this is the expected/default path)."
fi

echo ""
echo "Building the image (first build downloads ~1-2GB of Python/torch packages; can take several minutes)..."
# TORCH_INDEX is exported above and consumed via docker-compose.yml's
# build.args (NOT passed as a one-off --build-arg flag here) so that this
# command and a plain `docker compose build` re-run later resolve to the
# exact same build-arg value and reliably hit the cached pip-install layer.
docker compose build

echo "Starting the container..."
APP_PORT=$APP_PORT docker compose up -d

echo ""
echo "Waiting for the API to respond (seed corpus + all 3 local AI models"
echo "download/warm up in the background on first boot — this can take a few minutes)..."
ATTEMPTS=0
until curl -fsS "http://localhost:${APP_PORT}/api/health" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ "$ATTEMPTS" -gt 60 ]; then
    echo "Timed out waiting for the app to respond. Check logs with: docker compose logs -f"
    exit 1
  fi
  sleep 3
done

echo ""
echo "✅ Lucent is running at: http://localhost:${APP_PORT}"
echo "   Admin login: admin@lucent.local / ChangeMe123!  (set ADMIN_PASSWORD in .env before real use)"
echo ""
echo "   Model/data warm-up may still be finishing in the background — watch progress with:"
echo "     docker compose logs -f"
echo "   Once 'Bootstrap: all models warm.' appears, run the full check with:"
echo "     ./scripts/verify_e2e.sh"
echo ""
echo "   Next time, just run: ./scripts/run.sh"
