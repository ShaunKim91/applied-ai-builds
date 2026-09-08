#!/usr/bin/env bash
# Manually (re-)trigger seed-corpus indexing inside the running container.
# Normally unnecessary — main.py's startup hook already does this
# automatically on first boot — but useful to force a re-check or to watch
# it happen synchronously with output. Idempotent: does nothing if any
# documents are already indexed (see routers/documents.py::index_seed_corpus).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose exec -T app python -c "
from app.routers.documents import index_seed_corpus

print('Indexing the seed corpus (Federalist Papers, English + Korean Wikipedia)...')
result = index_seed_corpus()
print(f'  result: {result}')
"
