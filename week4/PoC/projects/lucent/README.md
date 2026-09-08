# Lucent

**AI Knowledge Assistant** — a Week4 PoC, part of an AI engineering project portfolio, turning this week's topic (document embeddings, VectorDB retrieval, and citation-grounded generation) into a real streaming RAG chat product — not a single-question search box, a multi-turn assistant with real-time token streaming, inline citations, and an automated groundedness check on every answer.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts: **[`flowchart.md`](flowchart.md)**
> 🎨 **A third distinct visual identity** — translucent "glass" panels over a gradient mesh background, one geometric sans (Manrope) carrying all hierarchy by weight, and a floating rounded sidebar — a deliberate step up from the Week1-3 PoCs' opaque-surface dashboards, per this round's explicit request for a more advanced, more transparent, more polished UI. See `architecture.md`'s UI section.
> 🧭 Deliberately engineered beyond a typical first-pass implementation of this pattern — see `architecture.md` §2 for exactly what's upgraded and why.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| ◈ **Chat** | `multilingual-e5-small` (retrieve) + optional `ms-marco-MiniLM-L-6-v2` (rerank) + `Qwen2.5-0.5B` local or `qwen/qwen3-8b` via OpenRouter (opt-in) | Ask a question, watch the answer stream in token by token, click a `[n]` citation to jump to its source, see a live groundedness badge |
| ▤ **Documents** | `multilingual-e5-small` (indexing) | Browse the bundled bilingual knowledge base (85 Federalist Papers essays in English + a Korean Wikipedia article on the same topic) or upload your own txt/md/pdf |
| ⬡ **Retrieval Lab** | Both retrieval models, shown side by side | See exactly how cross-encoder reranking changes (or doesn't change) a bi-encoder's top result for the same query |
| ⚙ **Admin** | — | Users, an AI-call audit trail, live model status, and a real usage-analytics dashboard (latency chart, groundedness pass rate, retrieval-mode split) |

**Four AI models** are wired in — three run 100% locally with no API key, and one (OpenRouter's `qwen/qwen3-8b`) is a strictly opt-in, user-toggled upgrade, following the same "local-default, cloud-opt-in, fails independently" hybrid pattern used throughout this project series (and the Week1-3 PoCs).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows), ~10GB free disk, internet access for the one-time model/data download.

```bash
cd week4/PoC/projects/lucent
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8750`). The three local AI models and the seed corpus continue downloading/indexing in the background on first boot (watch with `docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model isn't warm yet.

```bash
./scripts/run.sh              # every subsequent time — fast, reuses the built image
./scripts/stop.sh             # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh       # run the full end-to-end check (see below)
./scripts/download_models.sh  # (optional) force-download/verify all 3 local AI models via CLI
./scripts/download_data.sh    # (optional) force-refresh the seed corpus index
```

Everything — model downloads included — is driven entirely by shell scripts; nothing requires manual `docker exec`, a notebook, or clicking through the UI.

**Demo admin login**: `admin@lucent.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env` before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells commonly used for `.sh`-script-driven setups like this one).

## Project layout

```
lucent/
├── backend/           FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py          entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py        all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py        SQLAlchemy ORM (SQL storage)
│   │   ├── vectorstore.py   Chroma PersistentClient wrapper (vector storage)
│   │   ├── rag.py           shared retrieve(-then-rerank) pipeline used by chat + retrieval lab
│   │   ├── security.py      JWT + bcrypt auth
│   │   ├── ml/               embeddings.py · reranker.py · llm.py (+ streaming) · groundedness.py
│   │   ├── etl/               seed_corpus.py · chunking.py
│   │   └── routers/          auth · documents · chat (streaming) · retrieval · admin · health
│   └── verify_e2e.py   end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Chat, Documents, RetrievalLab, Admin, Login)
├── docker/Dockerfile   multi-stage build (Node build stage -> Python-only runtime image)
├── docker-compose.yml  single service, named volumes, auto-selected host port
├── scripts/            setup.sh · run.sh · stop.sh · verify_e2e.sh · download_data.sh · download_models.sh
├── data/SOURCES.md     dataset provenance, licenses, direct download links
├── architecture.md     system diagrams (Mermaid) + production-scaling notes + cost estimate
├── flowchart.md        per-feature function-level flowcharts (Mermaid)
└── docs/guide.html     all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Same reasoning as the Week1-3 PoCs, doubly true here: a typical first-pass implementation of this RAG pattern is a Streamlit app, fine for a single-session classroom exercise, but Lucent needs real token-by-token streaming (via `StreamingResponse` + `fetch()`/`ReadableStream` on the client — not something Streamlit's rerun-on-interaction model does natively), a multi-turn chat history, and full control over the glass design system. See `architecture.md` §2 for the specific, concrete upgrades over that baseline.

## Why TypeScript, not just Python

Same reasoning as the Week1-3 PoCs — the frontend is TypeScript (React + Vite + Tailwind) because that's what real commercial products pair with a Python AI backend; Node itself never runs in the deployed container (see the multi-stage `docker/Dockerfile`).

## A note on groundedness checking

Every chat answer is checked two ways before being shown as "grounded": every `[n]` citation marker must reference a source that was actually retrieved (a structural check, no AI model needed), and every sentence of the answer must be semantically similar enough to at least one retrieved chunk (an embedding-similarity check, reusing the same bi-encoder that did retrieval). This is a real, computed signal — not a static badge — and it can and does show "partially grounded" on real generations that drift from their sources. See `backend/app/ml/groundedness.py` and `docs/guide.html`'s limitations section for what this check does and doesn't catch.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no mocks) — including actually consuming the streaming response as a real client would, not just checking the endpoint returns 200: wait for all 3 local models to report warm → signup → JWT auth → confirm the seed corpus (85 Federalist essays + a Korean Wikipedia article) is indexed → upload a document → create a chat session → send a streamed message and assemble the tokens → send a message with cross-encoder reranking enabled → send a genuinely Korean-language question and confirm real cross-lingual retrieval → compare bi- vs. cross-encoder retrieval → confirm a regular user is correctly forbidden from `/api/admin/*` → confirm the admin account can read system status and analytics. Actual results from this build are recorded in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Data & licenses

Two real, public-source knowledge-base seeds, downloaded automatically (no manual step, no account/API key needed) — full citations and direct download links in [`data/SOURCES.md`](data/SOURCES.md):

- **English**: *The Federalist Papers* (85 essays), Project Gutenberg #18 — a work of the U.S. founding era, public domain.
- **Korean**: the Korean Wikipedia article "연방주의자 논집" (CC BY-SA 4.0) — directly on-topic with the English corpus, chosen specifically to make the multilingual embedding model's cross-lingual retrieval claim something a real question can demonstrate.

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and datasets cited throughout `docs/guide.html` and `data/SOURCES.md`. No application code was copied from another repository — though its architecture deliberately reuses proven patterns (auth, bootstrap isolation, readiness probing, retrieve-then-rerank comparison UX) from this author's own Week1-3 PoCs, and its embedding model choice was made specifically for its multilingual coverage (load-bearing for the cross-lingual retrieval demo).

## License

Portfolio PoC — see the top-level repository for licensing context. Third-party datasets/models retain their own licenses as documented in `data/SOURCES.md`.
