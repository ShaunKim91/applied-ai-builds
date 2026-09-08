# VoxIQ

**AI Meeting & Knowledge Intelligence Platform** — part of an AI engineering project portfolio, showing how four distinct AI techniques (embeddings & reranking, audio ASR, code-execution sandboxing, and LLM internals) come together in a single, commercial-grade product rather than four separate demos.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts: **[`flowchart.md`](flowchart.md)**
> 🧭 Built on the same proven template as an earlier product in this series, CommerceIQ — see that project's `debug/` for hardening this build applies from day one.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| 🎙️ **Meeting Transcription** | Whisper (`tiny`) | Transcribe your own audio, or one-click transcribe a public-domain sample (a JFK speech + 5 LibriSpeech clips) |
| 🔎 **Knowledge Search** | `all-MiniLM-L6-v2` (bi-encoder) + `ms-marco-MiniLM-L-6-v2` (cross-encoder) | Search a real archive of 7 U.S. Federal Reserve (FOMC) meeting minutes plus your transcribed meetings, with bi-encoder vs. cross-encoder rankings shown side-by-side |
| 🧮 **Analytics Agent** | `Qwen2.5-0.5B-Instruct` (local) or `qwen/qwen3-8b` via OpenRouter (opt-in) | Ask a question in plain language; an LLM writes Python, which runs in an isolated local sandbox over your meeting data |
| 🔤 **Tokenizer & Attention Explorer** | GPT-2 | See real tokenization + a self-attention heatmap for any text you type |
| 🛠️ **Admin Console** | — | Manage users, browse the AI-call audit trail, see live model/data status |

**Six AI models** are wired in — five run 100% locally with no API key (the project brief's "local models as the primary approach"), and one (OpenRouter's `qwen/qwen3-8b`) is a strictly opt-in, user-toggled upgrade, following the same "local-default, cloud-opt-in, fails independently" hybrid pattern used throughout this project series (including the CommerceIQ PoC).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows), ~10GB free disk, internet access for the one-time model/data download.

```bash
cd 2nd_week/PoC/projects/voxiq
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8730`). The five local AI models and both public datasets continue downloading/warming in the background on first boot (watch with `docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model isn't warm yet.

```bash
./scripts/run.sh              # every subsequent time — fast, reuses the built image
./scripts/stop.sh             # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh       # run the full end-to-end check (see below)
./scripts/download_models.sh  # (optional) force-download/verify all 5 local AI models via CLI
./scripts/download_data.sh    # (optional) force-refresh the public datasets + FOMC index
```

Everything — model downloads included — is driven entirely by shell scripts; nothing requires manual `docker exec`, a notebook, or clicking through the UI.

**Demo admin login**: `admin@voxiq.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env` before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells already used by this project series' other `env_set_up.sh`/`run.sh` scripts).

## Project layout

```
voxiq/
├── backend/           FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py          entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py        all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py        SQLAlchemy ORM (SQL storage)
│   │   ├── vectorstore.py   Chroma wrapper w/ pure-Python fallback (vector storage)
│   │   ├── security.py      JWT + bcrypt auth
│   │   ├── ml/               embeddings.py · reranker.py · whisper_asr.py · llm.py · sandbox.py · tokenizer_explorer.py
│   │   ├── etl/               audio_samples.py · fomc_minutes.py  (public dataset downloads + chunking)
│   │   └── routers/          auth · meetings · search · sandbox · tokenizer · admin · health
│   └── verify_e2e.py   end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Meetings, Search, Sandbox, Tokenizer, Admin, Login)
├── docker/Dockerfile   multi-stage build (Node build stage -> Python-only runtime image, + ffmpeg for Whisper)
├── docker-compose.yml  single service, named volumes, auto-selected host port
├── scripts/            setup.sh · run.sh · stop.sh · find_free_port.sh · download_data.sh · download_models.sh · verify_e2e.sh
├── data/SOURCES.md     dataset provenance, licenses, direct download links
├── architecture.md     system diagrams (Mermaid) + production-scaling notes + cost estimate
├── flowchart.md        per-feature function-level flowcharts (Mermaid)
└── docs/guide.html     all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Same reasoning as the CommerceIQ PoC: client-side routing across 6 distinct views, a real side-by-side comparison UI (bi- vs. cross-encoder results) and an attention heatmap that Streamlit's component set can't cleanly express, a persistent auth session, and a typed REST API (`/docs` for free via FastAPI). See `architecture.md` §2.

## Why TypeScript, not just Python

Same reasoning as the CommerceIQ PoC — the frontend is TypeScript (React + Vite + Tailwind) because that's what real commercial products pair with a Python AI backend; Node itself never runs in the deployed container (see the multi-stage `docker/Dockerfile`).

## A note on the local code sandbox

The Analytics Agent's code execution is a **teaching-grade** isolation boundary (subprocess + OS resource limits + a restricted `__builtins__` set) — a common "local fallback" design for this kind of code-execution feature, reproduced faithfully here as the default (and, since this build has no E2B API key, *only validated*) execution path. It is explicitly **not** a production security boundary — see `backend/app/ml/sandbox.py`'s module docstring and `docs/guide.html`'s limitations section for what real isolation requires.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no mocks): wait for all 5 local models to report warm → signup → JWT auth → list/transcribe sample audio (Whisper) → transcribe an uploaded file → knowledge search (bi- vs. cross-encoder) → analytics agent (LLM-generated code executed in the sandbox) → tokenizer/attention explorer → confirm a regular user is correctly forbidden from `/api/admin/*` → confirm the admin account can read it. Actual results from this build are recorded in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Data & licenses

Two public data sources, both downloaded automatically (no manual step, no account/API key needed) — full citations and direct download links in [`data/SOURCES.md`](data/SOURCES.md):

- **Sample audio**: `openai/whisper`'s own `jfk.flac` test asset (public domain U.S. presidential address) + 5 clips from `hf-internal-testing/librispeech_asr_dummy` (LibriSpeech, CC BY 4.0).
- **FOMC meeting minutes**: 7 real U.S. Federal Reserve meeting records (`federalreserve.gov`, public-domain government publications).

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and datasets cited throughout `docs/guide.html` and `data/SOURCES.md`. No external application code was copied from another repository.

## License

Portfolio PoC — see the top-level repository for licensing context. Third-party datasets/models retain their own licenses as documented in `data/SOURCES.md`.
