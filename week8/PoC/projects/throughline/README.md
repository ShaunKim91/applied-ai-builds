# Throughline

**A LangChain-based conversational-memory copilot for Fenwick Mutual** — a Week8 PoC, part of an
AI engineering project portfolio, and the third product in the "Fenwick Mutual" suite alongside
Week6's Verity (claims research) and Week7's Threshold (guarded claims-payout agent).
Throughline is for **Marcus Webb**, a Policyholder Services representative handling 50-70 inbound
calls a day about billing, coverage, and policy changes: he currently loses context every time a
caller re-explains something already stated earlier in the same call, or calls back next week about
the same issue with no record of the first conversation waiting for him.

> 📄 Full bilingual (EN default / 한국어) operations guide with screenshots, architecture diagrams,
> hardware requirements, and cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts:
> **[`flowchart.md`](flowchart.md)**
> 🧵 **Shares the "Fenwick Ledger" design system with Verity and Threshold** — a "ledger ink" indigo
> as Throughline's own primary accent, copper shared as the suite's secondary color, the same
> Fraunces + IBM Plex Sans + IBM Plex Mono type system, and the same "dossier tab-binder" navigation
> — one connected product suite for one fictional company, not three unrelated weekly builds. See
> `architecture.md` §3.
> 📈 Deliberately more advanced than a typical first-pass implementation of this same LangChain-agent
> pattern — one that never persists conversation memory (a self-documented gap in that kind of
> baseline build), routes tools with a brittle regex matcher, and uses a raw `eval()` calculator.
> See `architecture.md` §2.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| 🗂 **Cases** | `multilingual-e5-small` (semantic search) | Open a case for an incoming call, or search past cases by meaning, not keyword |
| 🧵 **Workspace** | `Qwen2.5-0.5B-Instruct` local (default) or `qwen/qwen3-8b` via OpenRouter (opt-in escalation) | Chat with the copilot as if relaying a live call — watch it route to a real tool, extract structured facts live into the "index card" sidebar, and correctly recall a fact stated several turns ago |
| ⚙ **Admin** | — | Live memory governance (window size / redaction toggle, editable at runtime), the full memory-conflict log, the retention/purge trail, users, a **hash-chained, tamper-evident audit trail** with a live integrity-verification action, real p50/p95/p99 latency metrics, and a daily OpenRouter spend cap |
| 🌐 **Public status page** | — | `/api/status` — model warm state, vector-store/OpenRouter reachability, uptime, current p95 — no login required |

## What "commercial-grade" concretely means here

Per this round's explicit request, shared with Verity's and Threshold's own commercial-grade
checklist: an `Organization` data model, access+rotating-refresh-token authentication with CSRF
protection and account lockout, a hash-chained audit log, a hand-rolled rate limiter, and real
observability (p50/p95/p99 latency, a structured error log, a public status page) — deliberately
reused verbatim rather than redesigned a third time (see `architecture.md` §0).

**Throughline-specific engineering upgrades over a typical first-pass implementation**:
- **Real LangChain LCEL composition** (`langchain-core==0.3.86`, verified against the actual
  installed package before writing any code that depends on it): `ChatPromptTemplate | Runnable |
  StrOutputParser()` chains for routing, structured memory extraction, and summarization — a typical
  baseline implementation imports `PromptTemplate` but only ever calls `.format()` on it, never a
  real `|` pipe.
- **Persisted, dual-strategy memory**: a SQL-backed `BaseChatMessageHistory` implementation +
  `trim_messages` window + a dedicated LCEL summarization chain — closing a well-known "memory not
  persisted, lost on restart" gap common to that kind of baseline build.
- **Structured-output tool routing** in place of a regex matcher, with a bounded retry and an honest
  fallback (never a silent guess) — see `debug/` for the real, measured first-try reliability found
  during this build.
- **Memory-conditioned tool auto-fill**: a stated preference (e.g. a callback time window) can fill a
  later tool call automatically — the one structural capability neither Verity nor Threshold has,
  since neither has a notion of the same external counterparty recurring across sessions.
- **The memory-write conflict guardrail**: a new fact never silently overwrites a confidently-known
  one — a disagreement is flagged for a human, logged either way. This project's own guardrail axis,
  structurally analogous to how Threshold gates a payout, applied instead to gating a memory write.
- **A real `ast`-whitelist safe evaluator**, closing the `eval()` shortcut both a typical baseline
  implementation and Threshold's own earlier calculator tool carry — and correcting a common piece of
  introductory advice recommending `ast.literal_eval` as a fix, even though it cannot evaluate
  `12 * 8` at all (verified).
- **Redaction at every trust boundary**: persistence, the OpenRouter escalation call, and the live
  Workspace sidebar all pass through the same pattern-based PII redaction — with an explicit, honest
  non-claim of certified PII-detection accuracy (see `docs/guide.html`).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/), ~5GB free disk,
internet access (one-time model download; the running app itself needs no network except the opt-in
OpenRouter escalation).

```bash
cd week8/PoC/projects/throughline
./scripts/setup.sh
```

The script prints the URL once the API responds (e.g. `http://localhost:8800`). Both local AI models
continue loading in the background on first boot — the UI is usable immediately.

```bash
./scripts/run.sh              # every subsequent time — fast
./scripts/stop.sh             # stop WITHOUT deleting the container or its data
./scripts/verify_e2e.sh       # full 31-check verification — makes one real, small OpenRouter call
./scripts/download_models.sh  # (optional) force-download/verify both local models via CLI
```

**Demo admin login**: `admin@fenwickmutual.example` / `ChangeMe123!` (change `ADMIN_PASSWORD` in
`.env` before any real use). Or sign up your own account from the login page.

## Project layout

```
throughline/
├── backend/             FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py           entrypoint, startup bootstrap, insecure-defaults guard, SPA serving
│   │   ├── config.py         all settings, incl. memory-window default + redaction toggle
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, CallerCase, ConversationTurn, MemoryFact, MemoryConflictLog, RetentionRequest, MemorySetting, hash-chained AuditLog, ErrorLog
│   │   ├── security.py       JWT access+refresh tokens, CSRF, account lockout (shared architecture with Verity/Threshold)
│   │   ├── rate_limit.py     hand-rolled in-memory sliding-window limiter
│   │   ├── audit.py          hash-chained audit logging + chain verification
│   │   ├── metrics.py        real p50/p95/p99 latency tracking
│   │   ├── chains/            llm_runnable.py (the shared local-model Runnable) · memory_store.py (SQL history + window/summary) · router.py (structured-output tool routing) · extraction.py (structured memory extraction + conflict guardrail) · tools.py (5 safe tools) · orchestrator.py (prepare/stream/finalize)
│   │   ├── ml/llm.py          OpenRouter escalation (redacted at the boundary, zero tool-calling capability by design)
│   │   ├── ml/redaction.py    pattern-based PII redaction, one function, three call sites
│   │   ├── ml/safe_eval.py    ast-whitelist arithmetic evaluator
│   │   └── routers/            auth · cases (create/list/search/messages SSE/escalate/purge/resolve) · admin · status · health
│   └── verify_e2e.py    31-check end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" design system
├── docker/Dockerfile    multi-stage build
├── docker-compose.yml   single service, named volumes, auto-selected host port (8800+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      system diagrams (Mermaid) + baseline-comparison table + security detail
├── flowchart.md         per-feature function-level flowcharts (Mermaid)
└── docs/guide.html      all-in-one bilingual operations guide
```

## The memory-write conflict guardrail

A new extraction never silently overwrites an already-confident `MemoryFact` — see
`chains/extraction.py`. When a `stated` value conflicts with another `stated` value, the old value is
kept and the disagreement is logged as a pending item for a human to resolve (from the Workspace UI);
every other overwrite (a higher-confidence value replacing a lower one, or vice versa correctly
refused) is still logged, never silent. This is Throughline's own guardrail axis — not a borrowed
payout-style HITL gate (all of this product's tools are safe/informational; that risk surface belongs
to Threshold), but a memory-integrity gate native to what this product actually does.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no
mocks): health/warm-wait → signup → CSRF enforcement → a real tool-calling run reaching the correct
answer → a memory-recall regression (a real bug found this build, see `debug/issue-02`) → structured
fact persistence → memory-conditioned tool auto-fill → the conflict guardrail → conflict resolution →
a real window-to-summary transition (another real bug found this build, see `debug/issue-03`) →
redaction-boundary verification → the safe evaluator (correct arithmetic AND rejected unsafe input) →
the purge cascade → semantic case search → admin memory settings/conflict log/retention log → a $0
budget cap block → a real OpenRouter escalation → hash-chained audit log + a direct tamper-detection
regression → rate-limiter regression → account lockout → refresh-token rotation → public status page
→ real metrics/error-log endpoints → admin permission boundaries. Actual results from this build are
in [`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Credit

Original work, using publicly documented model IDs, APIs, and libraries cited in `docs/guide.html`.
Architecture deliberately reuses proven patterns (auth foundations, bootstrap isolation, readiness
probing, streaming SSE) from this project series' own earlier PoCs and this round's own
Verity/Threshold builds, substantially extended with real `langchain-core` LCEL composition for this
round's own focus. Local-model choice and its tuned generation settings were verified directly against
the real model's documented behavior, not assumed.

## License

Portfolio project — see the top-level repository for licensing context. Third-party libraries/models
retain their own licenses as documented in `docs/guide.html`.
