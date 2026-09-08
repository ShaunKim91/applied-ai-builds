#!/usr/bin/env bash
# Manually (re-)trigger the public-dataset download inside the running
# container. Normally unnecessary — main.py's startup hook already does this
# automatically on first boot — but useful to force a re-check or to watch
# it happen synchronously with output.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose exec -T app python -c "
from app.etl.online_retail import ensure_online_retail_daily
from app.etl.sample_catalog import ensure_sample_images
from app.config import settings

print('Downloading UCI Online Retail dataset (CC BY 4.0)...')
series = ensure_online_retail_daily(settings.data_dir)
print(f'  ready: {len(series)} daily revenue rows.')

print('Downloading Grocery Store Dataset sample images (MIT License)...')
paths = ensure_sample_images(settings.data_dir)
print(f'  ready: {len(paths)} sample images.')
"
