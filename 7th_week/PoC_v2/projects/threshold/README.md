# Threshold

**A guardrailed ReAct agent console for Fenwick Mutual** — a Week7 PoC_v2, and a complete,
commercial-grade rebuild of the earlier "Cradle" PoC. Threshold is for **Priya Nakamura**, Claims Processing Team Lead over 22 examiners in Fenwick
Mutual's Property Claims Payments unit: her examiners lose a third of every claim's cycle time
bouncing between systems for routine lookups, and she needs a hard guarantee that no payout above a
threshold can ever bypass a supervisor's review.

> 📄 Full bilingual (EN default / 한국어) operations guide with screenshots, architecture diagrams,
> hardware requirements, and cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts:
> **[`flowchart.md`](flowchart.md)**
> 🛡️ **Shares the "Fenwick Ledger" design system with Verity** (Week6's companion rebuild) —
> copper as Threshold's own primary accent, bottle-green shared as the suite's secondary color,
> the same Fraunces + IBM Plex Sans + IBM Plex Mono type system, and the same "dossier tab-binder"
> navigation — one connected product suite for one fictional company, not two unrelated weekly
> builds. See `architecture.md` §3.
> 📈 Deliberately more advanced than a typical first-pass implementation of this pattern —
> which typically checks a guardrail in the wrong order and builds Human-in-the-Loop
> approval as a feature it never actually wires into the app. See `architecture.md` §2.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| 🛡️ **Console** | `Qwen2.5-0.5B-Instruct` local (default) or `qwen/qwen3-8b` via OpenRouter (opt-in escalation) | Ask the agent something — watch it think, act, and observe in real time, one step at a time |
| ✓ **Approvals** | — | A real Human-in-the-Loop queue: a payout over the admin-set threshold actually pauses the run; approve or deny it here, and the run actually resumes |
| 📜 **History** | `multilingual-e5-small` (indexing past runs) | Semantic search over every past agent run — finds by meaning, not keyword |
| ⚙ **Admin** | — | Live guardrail settings (allowed tools / step limit / cost cap / **amount-aware payout threshold**, editable at runtime), users, a **hash-chained, tamper-evident audit trail** with a live integrity-verification action, real p50/p95/p99 latency metrics, and a daily OpenRouter spend cap |
| 🌐 **Public status page** | — | `/api/status` — model warm state, vector-store/OpenRouter reachability, uptime, current p95 — no login required |

## What "commercial-grade" concretely means here

Per this round's explicit request, shared with Verity's own commercial-grade checklist (see that
project's README for the full list): an `Organization` data model, access+rotating-refresh-token
authentication with CSRF protection and account lockout, a hash-chained audit log, a hand-rolled
rate limiter, and real observability (p50/p95/p99 latency, a structured error log, a public status
page) — none of which the predecessor Cradle PoC (or any earlier PoC in this project series) implemented.

**Threshold-specific engineering upgrades over Cradle**:
- **Amount-aware HITL**: Cradle's Human-in-the-Loop gate was a flat per-tool-name set — a gated tool
  was *always* paused regardless of amount. Threshold's `issue_claim_payout` only pauses when the
  requested amount exceeds an admin-configurable threshold (default $2,500, illustrative) — a small
  payout flows straight through, a large one genuinely waits for a human.
- **The corrected guardrail order made visible, not just implemented**: the Admin → Guardrails tab
  explicitly explains *why* permission is checked before cost cap — a transparency feature, not
  just a silent fix.

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/), ~5GB free disk,
internet access (one-time model download; the running app itself needs no network except the opt-in
OpenRouter escalation).

```bash
cd 7th_week/PoC_v2/projects/threshold
./scripts/setup.sh
```

The script prints the URL once the API responds (e.g. `http://localhost:8790`). Both local AI models
continue loading in the background on first boot — the UI is usable immediately.

```bash
./scripts/run.sh              # every subsequent time — fast
./scripts/stop.sh             # stop WITHOUT deleting the container or its data
./scripts/verify_e2e.sh       # full 26-check verification — makes one real, small OpenRouter call
./scripts/download_models.sh  # (optional) force-download/verify both local models via CLI
```

**Demo admin login**: `admin@fenwickmutual.example` / `ChangeMe123!` (change `ADMIN_PASSWORD` in
`.env` before any real use). Or sign up your own account from the login page.

## Project layout

```
threshold/
├── backend/             FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py           entrypoint, startup bootstrap, insecure-defaults guard, SPA serving
│   │   ├── config.py         all settings, incl. per-tool cost + the amount-aware payout threshold
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, AgentRun/AgentStep, ApprovalRequest, GuardrailSetting, hash-chained AuditLog, ErrorLog
│   │   ├── security.py       JWT access+refresh tokens, CSRF, account lockout (shared architecture with Verity)
│   │   ├── rate_limit.py     hand-rolled in-memory sliding-window limiter
│   │   ├── audit.py          hash-chained audit logging + chain verification
│   │   ├── metrics.py        real p50/p95/p99 latency tracking
│   │   ├── agent/             tools.py (7 claims-ops tools + quote-aware arg parsing) · react_loop.py (ReAct mechanics) · guardrails.py (corrected order + amount-aware HITL) · orchestrator.py (the resumable loop)
│   │   ├── ml/llm.py          OpenRouter escalation (zero tool-calling capability by design)
│   │   └── routers/            auth · agent (streaming) · approvals (HITL) · history · admin · status · health
│   └── verify_e2e.py    26-check end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" design system
├── docker/Dockerfile    multi-stage build
├── docker-compose.yml   single service, named volumes, auto-selected host port (8790+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      system diagrams (Mermaid) + engineering-depth comparison table + security detail
├── flowchart.md         per-feature function-level flowcharts (Mermaid)
└── docs/guide.html      all-in-one bilingual operations guide
```

## The corrected guardrail check order

The four safety guardrails (step limit → permission → cost cap → HITL) are checked in that exact
order — deliberately, and for a documented reason: a common bug in naive implementations of this
pattern checks cost cap *before* permission, mislabeling an unauthorized-tool attempt as a budget
event instead of a permission violation once the budget happens to already be exhausted. See
`debug/issue-01` in the predecessor Cradle PoC for the full write-up (unchanged this round — the
underlying bug pattern hasn't changed, and neither has the fix), and this project's own
Admin → Guardrails tab, which explains the reasoning directly in the UI.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no
mocks): health/warm-wait → signup → CSRF enforcement → a real tool-calling run reaching the correct
answer → a quoted-argument regression (a real bug found this build, see `debug/issue-01`) →
guardrail-order and amount-aware-HITL regressions → a real HITL pause→approve→resume flow AND a real
pause→deny→resume flow → step-limit/cost-cap stops → History semantic search → a $0 budget cap
block → a real OpenRouter escalation → hash-chained audit log + a direct tamper-detection regression
→ rate-limiter regression → account lockout → refresh-token rotation → public status page → real
metrics/error-log endpoints → admin permission boundaries. Actual results from this build are in
[`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Credit

Original work, using publicly documented model IDs, APIs, and libraries cited in
`docs/guide.html`. Architecture deliberately reuses proven patterns (auth foundations, bootstrap
isolation, readiness probing, streaming SSE, the resumable-run pattern) from this project series'
own earlier PoCs and this round's own Verity build, substantially hardened and extended for this
round's commercial-grade requirement. ReAct loop design follows the standard Thought→Action→Observation
pattern; local-agent model choice (Qwen2.5-0.5B-Instruct) reflects a small, openly-licensed
instruct model suitable for on-device tool-calling.

## License

Course PoC — see the top-level repository for licensing context. Third-party libraries/models
retain their own licenses as documented in `docs/guide.html`.
