#!/usr/bin/env bash
# Stops the container WITHOUT deleting it or its data/model-cache volumes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose stop
echo "Throughline stopped (container and data preserved). Resume with ./scripts/run.sh"
