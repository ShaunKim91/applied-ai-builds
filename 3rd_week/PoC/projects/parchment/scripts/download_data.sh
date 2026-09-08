#!/usr/bin/env bash
# Manually (re-)trigger sample-document preparation inside the running
# container. Normally unnecessary — main.py's startup hook already does
# this automatically on first boot — but useful to force a re-check or to
# watch it happen synchronously with output.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose exec -T app python -c "
from app.etl.sample_receipts import ensure_sample_receipts
from app.etl.sample_pdf import ensure_sample_pdf
from app.config import settings

print('Generating synthetic sample receipts (Pillow-drawn, no PII)...')
samples = ensure_sample_receipts(settings.data_dir)
print(f'  ready: {len(samples)} sample receipt images.')

print('Downloading sample PDF (Fed Monetary Policy Report, public domain)...')
path = ensure_sample_pdf(settings.data_dir)
print(f'  ready: {path}' if path else '  FAILED (offline?) — upload your own PDF instead.')
"
