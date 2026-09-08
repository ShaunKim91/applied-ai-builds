#!/usr/bin/env bash
# Stops the container WITHOUT deleting it (or its data/model-cache volumes).
# `docker compose stop` — never `down` — so re-running scripts/run.sh later
# resumes instantly with no re-download of models or datasets.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose stop
echo "Container stopped (kept on disk — data & model cache are preserved)."
echo "Resume with: ./scripts/run.sh"
echo "(Only if you really want to delete everything: docker compose down -v)"
