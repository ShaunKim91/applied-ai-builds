#!/usr/bin/env bash
# Force-download/verify all local AI models via CLI, without booting the
# full app — useful for pre-warming the HuggingFace cache volume.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

docker compose exec -T app python -c "
from app.ml import embeddings, reranker, llm
print('Embedding dim:', embeddings.dimension())
print('Reranker score:', reranker.rerank('test', ['a test document']))
print('Local LLM info:', llm.local_model_info())
"
