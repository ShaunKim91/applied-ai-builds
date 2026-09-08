#!/usr/bin/env bash
# Manually (re-)trigger downloading + loading both local AI models inside
# the running container. Normally unnecessary — main.py's startup hook
# already does this automatically in the background on first boot — but
# useful to force it synchronously (e.g. to pre-warm before a demo, or to
# confirm both models are genuinely present).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

echo "Downloading/loading both local AI models inside the container ..."
echo "(cached to the cradle_hf_cache volume, so this only really downloads"
echo " anything the very first time; later runs just verify.)"
echo ""

docker compose exec -T app python -c "
from app.ml import embeddings
from app.agent import react_loop
from app.config import settings

print(f'[1/2] {settings.embedding_model} (multilingual bi-encoder, for History search) ...')
info = embeddings.model_info()
print(f'      loaded: {info[\"dimension\"]}-dim output')

print(f'[2/2] {settings.local_agent_model} (local ReAct agent brain) ...')
info = react_loop.local_model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print()
print('Both local models are downloaded and loaded.')
"

echo ""
echo "OpenRouter (qwen/qwen3-8b, model-routing escalation) needs no download —"
echo "called over the network only when a user clicks 'Ask a bigger model"
echo "instead' on the Console page, using the key at"
echo "../../../../api_keys/openrouter.md (never downloaded/cached locally)."
