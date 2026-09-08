#!/usr/bin/env bash
# Manually (re-)trigger downloading + loading all 5 local AI models inside
# the running container. Normally unnecessary — main.py's startup hook
# already does this automatically in the background on first boot — but
# useful to force it synchronously (e.g. to pre-warm before a demo, or to
# confirm all 5 models are genuinely present) and to show explicitly, per
# model, that this is a scriptable CLI operation rather than something
# requiring the web UI.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

echo "Downloading/loading all 5 local AI models inside the container ..."
echo "(cached to the voxiq_hf_cache volume, so this only really downloads"
echo " anything the very first time; later runs just verify.)"
echo ""

docker compose exec -T app python -c "
from app.ml import embeddings, reranker, whisper_asr, llm, tokenizer_explorer
from app.config import settings

print(f'[1/5] {settings.embedding_model} (bi-encoder embeddings) ...')
info = embeddings.model_info()
print(f'      loaded: {info[\"dimension\"]}-dim output')

print(f'[2/5] {settings.reranker_model} (cross-encoder reranker) ...')
reranker.model_info()
print('      loaded')

print(f'[3/5] whisper-{settings.whisper_model} (speech-to-text) ...')
info = whisper_asr.model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[4/5] {settings.local_llm_model} (local LLM, analytics agent) ...')
info = llm.local_model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[5/5] {settings.tokenizer_model} (tokenizer + attention explorer) ...')
info = tokenizer_explorer.model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print()
print('All 5 local models are downloaded and loaded.')
"

echo ""
echo "OpenRouter (qwen/qwen3-8b) needs no download — it's called over the network"
echo "only when a user opts in from the Analytics Agent page, using the key at"
echo "../../../../api_keys/openrouter.md (never downloaded/cached locally)."
