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
echo "(cached to the parchment_hf_cache volume, so this only really downloads"
echo " anything the very first time; later runs just verify.)"
echo ""

docker compose exec -T app python -c "
from app.ml import ocr, vlm, llm, summarizer, embeddings
from app.config import settings

print('[1/5] tesseract (LSTM OCR engine) ...')
info = ocr.model_info()
print(f'      available: {info[\"loaded\"]}')

print(f'[2/5] {settings.vlm_model} (local vision-language model) ...')
info = vlm.model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[3/5] {settings.local_llm_model} (local LLM, OCR-text structuring) ...')
info = llm.local_model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[4/5] {settings.summarizer_model} (PDF summarization) ...')
summarizer.model_info()
print('      loaded')

print(f'[5/5] {settings.embedding_model} (duplicate-detection embeddings) ...')
info = embeddings.model_info()
print(f'      loaded: {info[\"dimension\"]}-dim output')

print()
print('All 5 local models are downloaded and loaded.')
"

echo ""
echo "OpenRouter (qwen/qwen3-8b) needs no download — it's called over the network"
echo "only when a user opts in from the PDF Summarizer page, using the key at"
echo "../../../../api_keys/openrouter.md (never downloaded/cached locally)."
