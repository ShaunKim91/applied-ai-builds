#!/usr/bin/env bash
# Manually (re-)trigger the public-dataset download + FOMC indexing inside
# the running container. Normally unnecessary — main.py's startup hook
# already does this automatically on first boot — but useful to force a
# re-check or to watch it happen synchronously with output.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose exec -T app python -c "
from app.etl.audio_samples import ensure_sample_audio
from app.routers.search import index_fomc_minutes
from app.config import settings

print('Downloading sample audio (jfk.flac + LibriSpeech CC BY 4.0 clips)...')
manifest = ensure_sample_audio(settings.data_dir)
print(f'  ready: {len(manifest)} sample audio files.')

print('Downloading + indexing FOMC meeting minutes (public domain, federalreserve.gov)...')
result = index_fomc_minutes()
print(f'  ready: {result[\"documents\"]} documents, {result[\"chunks_indexed\"]} searchable chunks indexed.')
"
