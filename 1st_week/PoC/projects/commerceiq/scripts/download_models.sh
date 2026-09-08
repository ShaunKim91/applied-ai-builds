#!/usr/bin/env bash
# Manually (re-)trigger downloading + loading all 4 local AI models inside
# the running container. Normally unnecessary — main.py's startup hook
# already does this automatically in the background on first boot — but
# useful to force it synchronously (e.g. to pre-warm before a demo, or to
# confirm all 4 models are genuinely present after a fresh setup.sh run)
# and to show explicitly, per-model, that this is a scriptable CLI
# operation rather than something requiring the web UI.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker compose ps --status running --services 2>/dev/null | grep -q app; then
  echo "The app container isn't running. Start it first with ./scripts/setup.sh or ./scripts/run.sh"
  exit 1
fi

echo "Downloading/loading all 4 local AI models inside the container ..."
echo "(HuggingFace Hub — cached to the commerceiq_hf_cache volume, so this only"
echo " really downloads anything the very first time; later runs just verify.)"
echo ""

docker compose exec -T app python -c "
from app.ml import vision, embeddings, llm, diffusion
from app.config import settings

print(f'[1/4] {settings.vit_model} (vision classification) ...')
info = vision.model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[2/4] {settings.embedding_model} (embeddings) ...')
info = embeddings.model_info()
print(f'      loaded: {info[\"dimension\"]}-dim output')

print(f'[3/4] {settings.local_llm_model} (local LLM) ...')
info = llm.local_model_info()
print(f'      loaded: {info[\"params\"]:,} params')

print(f'[4/4] {settings.diffusion_model} (diffusion / image generation) ...')
info = diffusion.model_info()
total = info['unet_params'] + info['text_encoder_params'] + info['vae_params']
print(f'      loaded: {total:,} params (UNet + text encoder + VAE)')

print()
print('All 4 local models are downloaded and loaded.')
"

echo ""
echo "OpenRouter (qwen/qwen3-8b) needs no download — it's called over the network"
echo "only when a user opts in from the Forecasting page, using the key at"
echo "../../../../api_keys/openrouter.md (never downloaded/cached locally)."
