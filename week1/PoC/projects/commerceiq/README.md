# CommerceIQ

**English** | [한국어](README.ko.md)

**AI Commerce Operations Platform** — a PoC that brings together three AI disciplines (Vision Transformers, diffusion image generation, and time-series forecasting/anomaly detection) in a single, commercial-grade product rather than three separate demos.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts: **[`flowchart.md`](flowchart.md)**

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| 🖼️ **Catalog Vision** | `WinKawaks/vit-tiny-patch16-224` (ViT) | Classify a product photo you upload, or one-click classify a sample from the Grocery Store Dataset |
| 🎨 **Generative Studio** | `segmind/tiny-sd` (distilled Stable Diffusion) | Generate a product/marketing image from a text prompt |
| 📈 **Demand Forecasting & Anomaly Radar** | `statsmodels` (Holt-Winters) + `Qwen/Qwen2.5-0.5B-Instruct` (local) or `qwen/qwen3-8b` via OpenRouter (opt-in) | Forecast daily revenue on real UK e-commerce transactions (UCI Online Retail), see flagged anomalies, and read an AI-written business insight |
| 🔎 **Semantic Catalog Search** | `intfloat/multilingual-e5-small` + Chroma vector store | Search classified catalog items with natural language, in Korean or English |
| 🛠️ **Admin Console** | — | Manage users, browse the AI-call audit trail, see live model/data status |

**Five AI models** are wired in — four run 100% locally with no API key (the project brief's "local models as the primary approach"), and one (OpenRouter's `qwen/qwen3-8b`) is a strictly opt-in, user-toggled upgrade, following a "local-default, cloud-opt-in, fails independently" hybrid pattern used consistently across this project series.

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows), ~10GB free disk, internet access for the one-time model/data download.

```bash
cd week1/PoC/projects/commerceiq
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8720`). The four local AI models and both public datasets continue downloading/warming in the background on first boot (watch with `docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model isn't warm yet.

```bash
./scripts/run.sh             # every subsequent time — fast, reuses the built image
./scripts/stop.sh            # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh      # run the full end-to-end check (see below)
./scripts/download_data.sh   # (optional) force-refresh the 2 public datasets
./scripts/download_models.sh # (optional) force-download/verify all 4 local AI models via CLI, no UI needed
```

Everything — model downloads included — is driven entirely by these shell scripts; nothing requires manual `docker exec`, a notebook, or clicking through the UI. `setup.sh`/`run.sh` already trigger model downloads automatically in the background on first boot; `download_models.sh` just exposes that same step as an explicit, synchronous CLI command (useful for pre-warming before a demo, or confirming all 4 models are really present).

**Demo admin login**: `admin@commerceiq.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env` before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells used by this project series' other `env_set_up.sh`/`run.sh` scripts).

## Project layout

```
commerceiq/
├── backend/           FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py          entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py        all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py        SQLAlchemy ORM (SQL storage)
│   │   ├── vectorstore.py   Chroma wrapper w/ pure-Python fallback (vector storage)
│   │   ├── security.py      JWT + bcrypt auth
│   │   ├── jobs.py          background job manager (diffusion generation)
│   │   ├── ml/               vision.py · diffusion.py · embeddings.py · llm.py · forecast.py
│   │   ├── etl/               online_retail.py · sample_catalog.py  (public dataset downloads)
│   │   └── routers/          auth · vision · generate · forecast · search · admin · health
│   └── verify_e2e.py   end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, CatalogVision, GenerativeStudio, Forecasting, Search, Admin, Login)
├── docker/Dockerfile   multi-stage build (Node build stage -> Python-only runtime image)
├── docker-compose.yml  single service, named volumes, auto-selected host port
├── scripts/            setup.sh · run.sh · stop.sh · find_free_port.sh · download_data.sh · verify_e2e.sh
├── data/SOURCES.md     dataset provenance, licenses, direct download links
├── architecture.md     system diagrams (Mermaid) + production-scaling notes + cost estimate
├── flowchart.md        per-feature function-level flowcharts (Mermaid)
└── docs/guide.html     all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Streamlit is a fine choice for a quick, single-purpose demo. This PoC intentionally goes further because the brief specifically asks for commercial-grade UI/UX: client-side routing between 6 distinct views, a designed chart (forecast + confidence band + anomaly markers) that Streamlit's built-in charts can't express, a persistent auth session, and a typed REST API (`/docs` for free via FastAPI) that a mobile client or another internal service could reuse later. See `architecture.md` §2 for the full reasoning.

## Why TypeScript, not just Python

The project brief encourages showing that GenAI/AX work isn't locked into one language. The frontend is TypeScript (React + Vite + Tailwind) precisely because that is what real commercial products pair with a Python AI backend — a typed component layer, hot-reloadable dev server, and a production build that ships as static files (Node itself never runs in the deployed container — see the multi-stage `docker/Dockerfile`).

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no mocks): wait for all 4 local models to report warm (via `GET /api/health/ready`) → signup → JWT auth → classify a sample image (ViT) → classify an uploaded image → submit and poll a diffusion generation job (tiny-sd) → run a forecast with the local LLM insight (Qwen2.5-0.5B) → semantic search (e5-small + Chroma) → confirm a regular user is correctly forbidden from `/api/admin/*` → confirm the admin account can read it. It prints a PASS/FAIL line per step. Actual results from this build are recorded in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Data & licenses

Two public datasets, both downloaded automatically (no manual step, no account/API key needed) — full citations and direct download links in [`data/SOURCES.md`](data/SOURCES.md):

- **UCI "Online Retail"** (CC BY 4.0) — real UK e-commerce transactions, used for demand forecasting.
- **GroceryStoreDataset sample images** (MIT License, Klasson et al., WACV 2019) — 20 product photos, used for the Catalog Vision demo.

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and datasets cited throughout `docs/guide.html` and `data/SOURCES.md`. No external application code was copied from another repository.

## License

Portfolio PoC — see the top-level repository for licensing context. Third-party datasets/models retain their own licenses as documented in `data/SOURCES.md`.
