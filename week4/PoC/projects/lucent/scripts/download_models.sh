#!/usr/bin/env bash
# Manually (re-)trigger downloading + loading all 3 local AI models inside
# the running container. Normally unnecessary — main.py's startup hook
# already does this automatically in the background on first boot — but
# useful to force it synchronously (e.g. to pre-warm before a demo, or to
# confirm all 3 models are genuinely present).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

echo "Downloading/loading all 3 local AI models inside the container ..."
echo "(cached to the lucent_hf_cache volume, so this only really downloads"
echo " anything the very first time; later runs just verify.)"
echo ""

docker compose exec -T app python -c "
from app.ml import embeddings, reranker, llm
from app.config import settings

print(f'[1/3] {settings.embedding_model} (multilingual bi-encoder) ...')
info = embeddings.model_info()
print(f'      loaded: {info[\"dimension\"]}-dim output')

print(f'[2/3] {settings.reranker_model} (cross-encoder reranker) ...')
reranker.model_info()
print('      loaded')

print(f'[3/3] {settings.local_llm_model} (local streaming LLM) ...')
info = llm.local_model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print()
print('All 3 local models are downloaded and loaded.')
"

echo ""
echo "OpenRouter (qwen/qwen3-8b) needs no download — it's called (and"
echo "streamed) over the network only when a user opts in from the Chat"
echo "page, using the key at ../../../../api_keys/openrouter.md (never"
echo "downloaded/cached locally)."
