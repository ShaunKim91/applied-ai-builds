#!/usr/bin/env bash
# Start (or resume) an already-set-up Cradle instance. Fast — reuses the
# built image and the persisted data/model-cache volumes from setup.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .port ]; then
  echo "No previous setup found. Run ./scripts/setup.sh first."
  exit 1
fi

# shellcheck source=./find_free_port.sh
source scripts/find_free_port.sh

APP_PORT=$(cat .port)

if docker compose ps --status running --services 2>/dev/null | grep -qx app; then
  echo "Cradle is already running: http://localhost:${APP_PORT}"
  exit 0
fi

if ! is_port_free "$APP_PORT"; then
  echo "Port $APP_PORT is currently occupied by something else — picking a new one."
  APP_PORT=$(find_free_port 8770)
  echo "$APP_PORT" >.port
  if grep -q '^APP_PORT=' .env 2>/dev/null; then
    sed -i.bak "s/^APP_PORT=.*/APP_PORT=$APP_PORT/" .env && rm -f .env.bak
  fi
fi

APP_PORT=$APP_PORT docker compose up -d
echo "Cradle: http://localhost:${APP_PORT}"
