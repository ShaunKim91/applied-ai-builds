# Verity

**A grounded claims-research assistant for Fenwick Mutual** — a Week5_1 PoC_v2, part of an AI
engineering project portfolio, and a complete, commercial-grade rebuild of the earlier "Compass"
PoC. Verity is for **Dana Whitfield**, a Senior Claims Research Analyst on Fenwick Mutual's SIU &
Compliance team: when a claim gets escalated past the front-line adjusters, she has hours — not
days — to produce a precedent brief that cites real governing regulations and prior rulings well
enough to survive a policyholder appeal or a Department of Insurance audit.

> 📄 Full bilingual (EN default / 한국어) operations guide with screenshots, architecture diagrams,
> hardware requirements, and cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts:
> **[`flowchart.md`](flowchart.md)**
> 📗 **A sixth distinct visual identity — "Fenwick Ledger"**: deep bottle-green + copper on a warm
> ivory/espresso ground, Fraunces + IBM Plex Sans + IBM Plex Mono, and a "dossier tab-binder"
> navigation (overlapping manila-style tab dividers that pull forward on selection) — shared, by
> deliberate design, with Threshold (Week5_2's companion rebuild) as one connected product suite for
> one fictional company, rather than yet another standalone weekly identity. See `architecture.md` §3.
> 🎯 **Built to answer "who is this for," explicitly** — every earlier product in this series
> (CommerceIQ, VoxIQ, Parchment, Lucent, and Verity's own predecessor Compass) used only a generic
> functional category name, never a named buyer persona. This rebuild exists specifically to fix that.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| ◈ **Research** | `multilingual-e5-small` + `ms-marco-MiniLM-L-6-v2` (rerank the fictional jurisdiction corpus) + `Qwen2.5-0.5B` local or `qwen/qwen3-8b` via OpenRouter (opt-in) | Ask a claims question, get a cited Quick Answer or a structured Precedent Brief (Issue / Governing Authority / Facts Applied / Recommendation / Sources), with fraud-signal highlighting and source-trust badges |
| 📚 **Library** | `multilingual-e5-small` (semantic search) | Search every past research report by meaning, not keyword |
| ⛈ **CAT Events** | — | Track named catastrophe/weather events as first-class objects; every related research report rolls up underneath |
| 📡 **Vendor Radar** | `Qwen2.5-0.5B` structured extraction, real live web search | Evaluate an AI/InsurTech vendor tool on Cost / Security / Approval-friction, grounded in real web results |
| ⚙ **Admin** | — | Users, a **hash-chained, tamper-evident audit log** with a live integrity-verification action, real p50/p95/p99 latency metrics, a structured error log, and daily OpenRouter budget governance |
| 🌐 **Public status page** | — | `/api/status` — model warm state, vector-store/OpenRouter reachability, uptime, current p95 — no login required |

## What "commercial-grade" concretely means here

Per this round's explicit request to build at commercial-grade quality (not PoC-grade), while
staying within the project's standing local-Docker-demo infrastructure constraint:

- **A public marketing landing page** before login — stating exactly who this is for and why, in
  contrast to every prior PoC's straight-to-login-screen default.
- **An `Organization` data model** (Fenwick Mutual seeded as one row) instead of a hardcoded
  singleton `id=1` settings row — structurally multi-tenant-ready without building a tenant switcher.
- **Access + rotating refresh tokens** in httpOnly/SameSite=Strict cookies (no token in
  JS-reachable storage), CSRF double-submit protection on every mutating request, and account
  lockout after repeated failed logins — replacing every prior PoC's single flat 24h JWT.
- **A hash-chained audit log**: every row stores a SHA-256 hash of its own content plus the previous
  row's hash; an admin action walks the chain and reports the exact point of any tampering.
- **A hand-rolled, single-process rate limiter** on auth and AI-invoking endpoints (explicitly
  documented as a demo-scale limitation — a real multi-instance deployment would need shared state).
- **Real observability**: per-route p50/p95/p99 latency (not just a request counter), a structured
  error log with request-correlation IDs, and a public status page.

See `architecture.md` §4 for the full checklist and what's explicitly out of scope (real cloud
deployment, billing integration, a working tenant switcher).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/), ~5GB free disk,
internet access (one-time model download; the opt-in OpenRouter escalation is the only runtime
network dependency beyond that — claims research itself is fully offline, see below).

```bash
cd week5_1/PoC_v2/projects/verity
./scripts/setup.sh
```

The script prints the URL once the API responds (e.g. `http://localhost:8780`). Three local AI
models continue loading in the background on first boot — the UI is usable immediately.

```bash
./scripts/run.sh              # every subsequent time — fast
./scripts/stop.sh             # stop WITHOUT deleting the container or its data
./scripts/verify_e2e.sh       # full 25-check verification — makes one real, small OpenRouter call
./scripts/download_models.sh  # (optional) force-download/verify all 3 local models via CLI
```

**Demo admin login**: `admin@fenwickmutual.example` / `ChangeMe123!` (change `ADMIN_PASSWORD` in
`.env` before any real use). Or sign up your own account from the login page.

## Why claims/jurisdiction research never touches the live web

Unlike the old Compass PoC (which searched the real live web via `ddgs`), Verity's claims research
is grounded **only** in a fully fictional, code-defined corpus (`backend/app/search/jurisdictions.py`)
covering six invented jurisdictions with invented statutes, case rulings, and DOI bulletins. Real
scraped web content about real states' real insurance law would be logically incoherent for a
fictional insurer, and would risk the LLM echoing real regulatory text as if Verity had verified it —
a real hallucination-adjacent risk this project's standing rule requires avoiding. The **separate**
Vendor Adoption Radar feature *does* use real live web search, since evaluating a real AI/InsurTech
vendor tool is genuinely real-world research. See that module's own doc comments for the full
reasoning.

## Project layout

```
verity/
├── backend/             FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py           entrypoint, startup bootstrap, insecure-defaults guard, SPA serving
│   │   ├── config.py         all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, ResearchSession/ReportEntry, CatEvent, hash-chained AuditLog, ErrorLog
│   │   ├── security.py       JWT access+refresh tokens, CSRF, account lockout
│   │   ├── rate_limit.py     hand-rolled in-memory sliding-window limiter
│   │   ├── audit.py          hash-chained audit logging + chain verification
│   │   ├── metrics.py        real p50/p95/p99 latency tracking
│   │   ├── vectorstore.py    Chroma PersistentClient wrapper
│   │   ├── ml/                embeddings.py · reranker.py · llm.py · ghost_citation.py (+ entity check) · groundedness.py · fraud_signals.py
│   │   ├── search/             jurisdictions.py (fictional corpus) · web_search.py (real, Radar-only) · rerank_pipeline.py
│   │   └── routers/            auth · research (streaming) · archive · cat_events · radar · admin · status · health
│   └── verify_e2e.py    25-check end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" design system
├── docker/Dockerfile    multi-stage build
├── docker-compose.yml   single service, named volumes, auto-selected host port (8780+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      system diagrams (Mermaid) + engineering-depth comparison table + security/observability detail
├── flowchart.md         per-feature function-level flowcharts (Mermaid)
└── docs/guide.html      all-in-one bilingual operations guide
```

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no
mocks): health/warm-wait → signup → CSRF enforcement → a real grounded quick-answer query → a real
precedent-brief query → ghost-citation/fraud-signal/entity-hallucination/source-trust regression
tests → CAT events → semantic library search → a real live-web vendor evaluation → cost-governance
$0 block → a real OpenRouter call → hash-chained audit log + a direct tamper-detection regression →
rate-limiter regression → account-lockout flow → refresh-token rotation (incl. reuse rejection) →
public status page → real metrics/error-log endpoints → admin permission boundaries. Actual results
from this build are in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Credit

Original work, using publicly documented model IDs, APIs, and libraries cited in
`docs/guide.html`. Architecture deliberately reuses proven patterns (auth foundations, bootstrap
isolation, readiness probing, streaming SSE, the daily-budget-cap governance pattern) from this
project series' own Week1-5_2 PoCs, substantially hardened and extended for this round's
commercial-grade requirement.

## License

Portfolio project — see the top-level repository for licensing context. Third-party libraries/models
retain their own licenses as documented in `docs/guide.html`.
