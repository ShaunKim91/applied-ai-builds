# Compass

**A web-search-grounded research assistant** — a Week5_1 PoC, part of an AI engineering project portfolio, turning this week's topic (search APIs, embedding-based reranking, and search+LLM grounding) into a real streaming research product: live web search, cross-encoder reranking, a streamed and cited report, an automated "ghost citation" check, a searchable archive of past research, a live comparison against OpenRouter's own managed web-search product, and a cost-governance budget cap a typical baseline implementation of this pattern never implements.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts: **[`flowchart.md`](flowchart.md)**
> 🧭 **A fourth distinct visual identity** — a navy "chart room" palette (brass + teal on deep navy, a faint chart-paper grid), a three-way type system (serif dispatch headlines, geometric-sans UI chrome, monospace citation metadata), a fixed "command console" search bar + collapsible icon rail, and real motion (a radar-sweep loading indicator, skeleton-shimmer source cards) — the first of these apps to default to dark rather than light. See `architecture.md`'s UI section.
> 📈 Deliberately more advanced than a typical baseline implementation of this pattern — whose default path calls **no LLM at all** (a rule-based template) — see `architecture.md` §2 for exactly what's upgraded and why.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| ◈ **Research** | `multilingual-e5-small` + `ms-marco-MiniLM-L-6-v2` (rerank live search results) + `Qwen2.5-0.5B` local or `qwen/qwen3-8b` via OpenRouter (opt-in) | Ask a question, watch Compass search the live web and stream a cited report, see a groundedness badge and a ghost-citation check on every answer |
| ▤ **Archive** | `multilingual-e5-small` (indexing past reports) | Semantic search over every past research report — finds by meaning, not keyword |
| ⬡ **Grounding Lab** | Compass's own pipeline vs. OpenRouter's managed web-search plugin | Compare two entire retrieval strategies side by side — latency, cost, and citations, not just two rerankers |
| ◎ **Trend Radar** | `Qwen2.5-0.5B` structured extraction | Evaluate an AI tool/trend across Cost / Security / Approval-friction lenses, grounded strictly in what was found |
| ⚙ **Admin** | — | Users, an AI-call audit trail, live model + web-search status, usage analytics, and a daily OpenRouter spend cap that auto-blocks the paid path once reached |

**Four AI models** are wired in — three run 100% locally with no API key (embeddings, reranker, local LLM), and the fourth (OpenRouter) is exercised two distinct ways, both strictly opt-in: an ordinary chat-completion call to synthesize Compass's own retrieved sources, and OpenRouter's own fully-managed web-search plugin. Live web search itself needs no key either — `ddgs` is free — with a deterministic mock fallback if it's ever rate-limited, following a standard mock-first resilience pattern.

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows), ~8GB free disk, internet access (one-time model download + live web search).

```bash
cd week5_1/PoC/projects/compass
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8760`). The three local AI models continue downloading/loading in the background on first boot (watch with `docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model isn't warm yet.

```bash
./scripts/run.sh              # every subsequent time — fast, reuses the built image
./scripts/stop.sh             # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh       # run the full end-to-end check (see below) — makes one real, small OpenRouter charge
./scripts/download_models.sh  # (optional) force-download/verify all 3 local AI models via CLI
```

Everything — model downloads included — is driven entirely by shell scripts; nothing requires manual `docker exec`, a notebook, or clicking through the UI.

**Demo admin login**: `admin@compass.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env` before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells already used by this project series' other `env_set_up.sh`/`run.sh` scripts).

## Project layout

```
compass/
├── backend/            FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py           entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py         all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py         SQLAlchemy ORM (SQL storage) — ReportEntry, BudgetSetting, etc.
│   │   ├── vectorstore.py    Chroma PersistentClient wrapper — indexes past reports for Archive search
│   │   ├── pipeline.py       shared search-then-rerank + prompt construction (Research + Trend Radar)
│   │   ├── security.py       JWT + bcrypt auth
│   │   ├── ml/                embeddings.py · reranker.py · llm.py (+ streaming + OpenRouter web-search) · groundedness.py · ghost_citation.py
│   │   ├── search/             web_search.py (ddgs + mock fallback) · rerank_pipeline.py
│   │   └── routers/            auth · research (streaming) · archive · grounding_lab · trend_radar · admin · health
│   └── verify_e2e.py    end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/            React + TypeScript + Vite + Tailwind SPA
│   └── src/             pages/ (Dashboard, Research, Archive, GroundingLab, TrendRadar, Admin, Login)
├── docker/Dockerfile    multi-stage build (Node build stage -> Python-only runtime image)
├── docker-compose.yml   single service, named volumes, auto-selected host port
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      system diagrams (Mermaid) + production-scaling notes + cost estimate
├── flowchart.md         per-feature function-level flowcharts (Mermaid)
└── docs/guide.html      all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Same reasoning as the Week1-4 PoCs, doubly true here: a typical baseline implementation of this pattern is a Streamlit app with no persistence, no auth, and (by default) no generation at all. Compass needs real token-by-token streaming (via `StreamingResponse` + `fetch()`/`ReadableStream` on the client), a persisted, searchable archive of past research, and full control over the navy/brass/teal design system. See `architecture.md` §2 for the specific, concrete upgrades over that baseline.

## Why the retrieval source has no seed corpus

Unlike Week4's Lucent (a fixed local document corpus), this week's whole point is *live* web-search grounding — there is nothing to pre-index. `data/README.md` explains what the `data/` directory holds instead (the runtime SQLite DB and the Chroma archive index, both created fresh on first boot).

## A note on the two verification layers

Every research report is checked two independent ways: `ml/groundedness.py` (reused from Week4) confirms every `[n]` citation index is valid and every sentence is embedding-similar to a retrieved source; `ml/ghost_citation.py` (new this week, generalizing a common introductory URL-verification technique) extracts every URL the model actually wrote in its answer and flags any that weren't in the real retrieved results — catching a different, web-search-specific failure mode (a paraphrased or invented citation URL) that the sentence-similarity check alone wouldn't necessarily catch. See `docs/guide.html`'s limitations section for what neither check catches.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no mocks) — including actually consuming the streamed report as a real client would: wait for all 3 local models + live web-search connectivity to report warm → signup → JWT auth → create a research session → send a streamed query (bi-encoder only, then with cross-encoder reranking) → confirm groundedness survives a history reload (a regression check for a real bug Week4's Lucent PoC shipped, see `../../debug/`) → unit-check the ghost-citation detector and the Trend Radar JSON extractor against real previously-observed edge cases → confirm Archive semantic search finds a just-created report → evaluate a real Trend Radar topic → confirm a $0 budget cap actually blocks the paid OpenRouter call → make one real OpenRouter web-search comparison call → confirm admin/regular-user permission boundaries. Actual results from this build are recorded in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and libraries cited throughout `docs/guide.html`. No application code was copied from another repository — though its architecture deliberately reuses proven patterns (auth, bootstrap isolation, readiness probing, streaming SSE infrastructure, groundedness checking) from this same project series' own Week1-4 PoCs, and its reranking model choice matches the reranker a typical baseline implementation of this pattern also uses.

## License

Portfolio project — see the top-level repository for licensing context. Third-party libraries/models retain their own licenses as documented in `docs/guide.html`.
