# Parchment

**AI Document Intelligence Workspace** — a Week3 PoC, part of an AI engineering project portfolio, showing how three techniques (computer-vision/multimodal image reading, PDF parsing + summarization, HTML table scraping) come together in a single, commercial-grade back-office tool rather than three disconnected demo tabs.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts: **[`flowchart.md`](flowchart.md)**
> 🧭 Built on the same proven template as the Week1/2 PoCs — see `architecture.md` §5 for the hardening this build inherits from day one.
> 🎨 **A visually distinct UI this round, by request** — a warm "parchment" palette, serif headings (Newsreader), and a top-tab layout, replacing the Week1/2 PoCs' cool-gray sidebar dashboard look. See `architecture.md`'s UI section for the full rationale.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| 🧾 **Receipts** | Tesseract (OCR) + Qwen2.5-0.5B (structuring) *vs.* SmolVLM-256M (direct read) | Upload a receipt photo, or try a synthetic sample — see the classic OCR+structuring pipeline and a local vision-language model's direct answer, side by side |
| 📄 **PDF Summarizer** | `distilbart-cnn-12-6` (local) or `qwen/qwen3-8b` via OpenRouter (opt-in) | Upload a PDF, or try the bundled real Fed report — get a summary with every number cross-checked against the source text |
| 🌐 **HTML Tables** | BeautifulSoup + pandas (no AI needed) | Paste any URL with data tables, or try a real Wikipedia sample — parse, preview, and export to CSV |
| 🗂️ **Document Library** | `all-MiniLM-L6-v2` (embeddings) + Chroma | See every processed document and automatically-flagged near-duplicates (embedding similarity — not a search/RAG feature, see below) |
| 🛠️ **Admin Console** | — | Manage users, browse the AI-call audit trail, see live model/data status |

**Six AI models** are wired in — five run 100% locally with no API key (the project brief's "local models as the primary approach"), and one (OpenRouter's `qwen/qwen3-8b`) is a strictly opt-in, user-toggled upgrade, following the same "local-default, cloud-opt-in, fails independently" hybrid pattern used throughout this project series (and the Week1/2 PoCs).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows), ~10GB free disk, internet access for the one-time model/data download.

```bash
cd 3rd_week/PoC/projects/parchment
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8740`). The five local AI models and the sample data continue downloading/warming in the background on first boot (watch with `docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model isn't warm yet.

```bash
./scripts/run.sh              # every subsequent time — fast, reuses the built image
./scripts/stop.sh             # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh       # run the full end-to-end check (see below)
./scripts/download_models.sh  # (optional) force-download/verify all 5 local AI models via CLI
./scripts/download_data.sh    # (optional) force-refresh the sample documents
```

Everything — model downloads included — is driven entirely by shell scripts; nothing requires manual `docker exec`, a notebook, or clicking through the UI.

**Demo admin login**: `admin@parchment.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env` before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells already used by this project series' other `env_set_up.sh`/`run.sh` scripts).

## Project layout

```
parchment/
├── backend/           FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py          entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py        all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py        SQLAlchemy ORM (SQL storage)
│   │   ├── vectorstore.py   Chroma wrapper w/ pure-Python fallback (vector storage)
│   │   ├── security.py      JWT + bcrypt auth
│   │   ├── ml/               ocr.py · vlm.py · llm.py · summarizer.py · embeddings.py · dedupe.py
│   │   ├── etl/               sample_receipts.py · sample_pdf.py · pdf_utils.py · html_utils.py
│   │   └── routers/          auth · receipts · pdfs · tables · library · admin · health
│   └── verify_e2e.py   end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Receipts, Pdfs, Tables, Library, Admin, Login)
├── docker/Dockerfile   multi-stage build (Node build stage -> Python-only runtime image,
│                       + tesseract-ocr/-kor + poppler-utils for OCR/PDF)
├── docker-compose.yml  single service, named volumes, auto-selected host port
├── scripts/            setup.sh · run.sh · stop.sh · verify_e2e.sh · download_data.sh · download_models.sh
├── data/SOURCES.md     dataset provenance, licenses, direct download links
├── architecture.md     system diagrams (Mermaid) + production-scaling notes + cost estimate
├── flowchart.md        per-feature function-level flowcharts (Mermaid)
└── docs/guide.html     all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Same reasoning as the Week1/2 PoCs: a typical first-pass implementation of this kind of tool tends to be Streamlit-based (a few tabs, no auth, no admin) — a fine choice for a quick single-session exercise, but this PoC targets commercial-grade depth: persistent auth, a role-gated admin console, a typed REST API (`/docs` for free via FastAPI), and — this round specifically — full design-system control (a custom serif/parchment visual identity that Streamlit's component set can't express). See `architecture.md` §2.

## Why TypeScript, not just Python

Same reasoning as the Week1/2 PoCs — the frontend is TypeScript (React + Vite + Tailwind) because that's what real commercial products pair with a Python AI backend; Node itself never runs in the deployed container (see the multi-stage `docker/Dockerfile`).

## A note on the Document Library's "duplicate detection" (not RAG)

The Document Library embeds every processed document and checks it for near-duplicates — a genuine vector-database-backed feature, but deliberately **not** a search or retrieval-augmented-generation (RAG) feature. A full embeddings + ChromaDB + retrieve-then-answer search feature is a substantial project in its own right; this PoC stays scoped to "turn unstructured documents into structured data" (its actual focus) and uses the vector store only for a narrow, genuinely different purpose (catching a re-submitted receipt/report) so it doesn't quietly grow into a second, half-built product. See `architecture.md` for the full reasoning.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no mocks): wait for all 5 local models to report warm → signup → JWT auth → extract a sample receipt (OCR+structuring vs. VLM, side by side) → reprocess the same sample and confirm it's flagged as a duplicate → extract an uploaded receipt → summarize the sample PDF (with numeric cross-check) → parse a sample HTML table → confirm the Document Library reflects the flagged duplicate → confirm a regular user is correctly forbidden from `/api/admin/*` → confirm the admin account can read it. Actual results from this build are recorded in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Data & licenses

Real and synthetic sample data, both handled automatically (no manual step, no account/API key needed) — full citations and direct download links in [`data/SOURCES.md`](data/SOURCES.md):

- **Receipts**: synthetic, Pillow-generated demo receipts (no real PII — real receipt images carry a well-known PII risk, so this project sidesteps the issue entirely rather than source real ones).
- **PDF**: a real Federal Reserve Monetary Policy Report (`federalreserve.gov`, public-domain U.S. government publication).
- **HTML tables**: a real Wikipedia page (CC BY-SA 4.0, attributed) with genuine, structured `<table>` data.

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and datasets cited throughout `docs/guide.html` and `data/SOURCES.md`. No application code was copied from another repository — its architecture deliberately reuses proven patterns (auth, bootstrap isolation, readiness probing) from this same author's own Week1/2 PoCs, and its topic/tab structure (image extraction, PDF summarization, HTML table scraping as three tabs) follows a common, general-purpose shape for this kind of document-intake tool.

## License

Portfolio project — see the top-level repository for licensing context. Third-party datasets/models retain their own licenses as documented in `data/SOURCES.md`.
