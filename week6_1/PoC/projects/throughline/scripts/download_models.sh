#!/usr/bin/env bash
# Force-download/verify both local AI models via CLI, without booting the
# full app — useful for pre-warming the HuggingFace cache volume.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

docker compose exec -T app python -c "
from app.ml import embeddings
from app.chains.llm_runnable import local_model_info
print('Embedding dim:', embeddings.dimension())
print('Local chat model info:', local_model_info())
"
