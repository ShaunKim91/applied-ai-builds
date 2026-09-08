#!/usr/bin/env bash
# Runs the full end-to-end verification suite (backend/verify_e2e.py)
# against the running container over real HTTP. NOTE: this makes one real
# OpenRouter call (~$0.001, see config.py) — see the "real OpenRouter call"
# step in verify_e2e.py.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

docker compose exec -T app python verify_e2e.py
