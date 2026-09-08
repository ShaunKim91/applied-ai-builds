# Cradle

**A local ReAct agent console with real safety guardrails** — a Week7 PoC, part of an AI
engineering project portfolio, turning agentic AI fundamentals (the Thought→Action→Observation
loop, a local LLM as the agent's own "brain," and the four guardrails that keep an autonomous agent
safe) into a real, running product: a local Qwen2.5-0.5B agent that actually calls tools, a layered
3D trace of its own reasoning, a genuinely-wired Human-in-the-Loop approval queue that a typical
first-pass implementation builds but never connects, a correctly-ordered guardrail check (a naive
implementation is easy to get wrong here), and an opt-in cloud escalation for when the local model
stalls.

> 📄 Full bilingual (한국어 default / English) operations guide with screenshots, architecture
> diagrams, hardware requirements, and cloud-cost estimates: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ System design: **[`architecture.md`](architecture.md)** · 🔀 Function-level flowcharts:
> **[`flowchart.md`](flowchart.md)**
> 🧸 **A fifth distinct visual identity, and the first with real 3D/spatial depth** — a
> high-lightness, low-saturation pastel "claymorphism" palette (dusty lilac + sage green on a
> soft off-white ground), a three-way type system (Quicksand rounded display + Plus Jakarta Sans UI
> chrome + Space Mono audit data), a floating pill-shaped nav bar, a mouse-reactive
> `perspective`/`rotateX`/`rotateY` tilt component reserved for a few hero surfaces, and a
> layered, slightly-rotated "stacked card" visualization of the agent's own reasoning steps. See
> `architecture.md` §3 for what's genuinely spatial versus decorative.
> 📈 Deliberately more advanced than a typical baseline implementation of this pattern —
> which a naive build can easily get wrong by checking a guardrail in the wrong order, and by
> building Human-in-the-Loop approval as a class feature it never actually wires into the app — see
> `architecture.md` §2 for exactly what's engineered further and why.

## What it does

| Module | AI model(s) | What you can try |
|---|---|---|
| ◈ **Console** | `Qwen2.5-0.5B-Instruct` local (default) or `qwen/qwen3-8b` via OpenRouter (opt-in escalation) | Ask the agent something — watch it think, act, and observe in real time, rendered as a layered 3D card stack, one step at a time |
| ✓ **Approvals** | — | A real Human-in-the-Loop queue: a gated tool call (`issue_refund`) actually pauses the run; approve or deny it here, and the run actually resumes |
| ▤ **History** | `multilingual-e5-small` (indexing past runs) | Semantic search over every past agent run — finds by meaning, not keyword |
| ⚙ **Admin** | — | Live guardrail settings (allowed tools / step limit / cost cap, editable at runtime), users, a full AI-call + tool-execution audit trail, usage analytics, and a daily OpenRouter spend cap for the opt-in escalation |

**Two AI models run 100% locally with no API key** (embeddings for History search, the local ReAct
agent brain) — a third, OpenRouter's `qwen/qwen3-8b`, is exercised strictly opt-in, for one
best-effort final-answer synthesis when the local agent stalls or a user wants a second opinion, not
a second independent tool-calling loop. Unlike every prior week's PoC, there is no live external
dependency (no web search, no fixed corpus) — the agent's only "world" is a small set of real,
locally-executed tools (calculator, date lookup, currency conversion, FAQ lookup, refund issuance).

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS or Windows),
~6GB free disk, internet access (one-time model download; the running app itself needs no network
except for the opt-in OpenRouter escalation).

```bash
cd week7/PoC/projects/cradle
./scripts/setup.sh      # first time: builds the image, picks a free port, starts the container
```

That's it — the script prints the URL once the API responds (e.g. `http://localhost:8770`). Both
local AI models continue downloading/loading in the background on first boot (watch with
`docker compose logs -f`); the UI is usable immediately and simply waits on first use if a model
isn't warm yet.

```bash
./scripts/run.sh              # every subsequent time — fast, reuses the built image
./scripts/stop.sh             # stop the container WITHOUT deleting it or its data
./scripts/verify_e2e.sh       # run the full end-to-end check (see below) — makes one real, small OpenRouter charge
./scripts/download_models.sh  # (optional) force-download/verify both local AI models via CLI
```

Everything — model downloads included — is driven entirely by shell scripts; nothing requires
manual `docker exec`, a notebook, or clicking through the UI.

**Demo admin login**: `admin@cradle.local` / `ChangeMe123!` (change `ADMIN_PASSWORD` in `.env`
before any real use). Or just sign up your own account from the login page.

On Windows, run these `.sh` scripts from Git Bash or WSL2 (the same shells already used by this
course's other `env_set_up.sh`/`run.sh` scripts).

## Project layout

```
cradle/
├── backend/            FastAPI app (Python 3.11) — see backend/app/
│   ├── app/
│   │   ├── main.py           entrypoint, startup bootstrap, SPA static serving
│   │   ├── config.py         all settings, incl. *_api_key_file references (no hardcoded secrets)
│   │   ├── models.py         SQLAlchemy ORM — AgentRun, AgentStep, ApprovalRequest, GuardrailSetting, BudgetSetting
│   │   ├── vectorstore.py    Chroma PersistentClient wrapper — indexes past runs for History search
│   │   ├── security.py       JWT + bcrypt auth
│   │   ├── agent/             tools.py · react_loop.py (Thought/Action/Observation, few-shot, streaming) ·
│   │   │                      guardrails.py (the corrected check order) · orchestrator.py (the resumable loop)
│   │   ├── ml/                embeddings.py · llm.py (OpenRouter escalation)
│   │   └── routers/            auth · agent (streaming) · approvals (HITL) · archive (History) · admin · health
│   └── verify_e2e.py    end-to-end smoke test (see scripts/verify_e2e.sh)
├── frontend/            React + TypeScript + Vite + Tailwind SPA
│   └── src/             pages/ (Dashboard, Console, Approvals, History, Admin, Login), components/TiltCard.tsx
├── docker/Dockerfile    multi-stage build (Node build stage -> Python-only runtime image)
├── docker-compose.yml   single service, named volumes, auto-selected host port
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      system diagrams (Mermaid) + baseline-comparison table + production-scaling notes
├── flowchart.md         per-feature function-level flowcharts (Mermaid)
└── docs/guide.html      all-in-one bilingual operations guide (see below)
```

## Why FastAPI + React instead of Streamlit

Same reasoning as the Week1-6 PoCs, doubly true here: a typical baseline implementation of this
pattern is a 2-tab Streamlit demo where the ReAct agent tab and a guardrail-class tab never talk to
each other, with no persistence, no auth, and HITL approval built as an unused class feature. Cradle
needs a resumable run that can actually pause for a real human decision — potentially long after the
original HTTP request ended — which needs a real database and a real approval-queue endpoint, not a
single Streamlit script's local variables. See `architecture.md` §2 for the specific, concrete
engineering beyond that baseline.

## Why there's no seed corpus this week

Unlike Week4's Lucent (a fixed document corpus) or Week6's Compass (live web search), this
week's retrieval surface is a small, fixed set of local Python functions the agent calls as tools —
there's nothing to pre-index. `data/README.md` explains what `data/` holds instead (the runtime
SQLite DB and the Chroma archive index over past runs, both created fresh on first boot).

## A note on the guardrail check order

The four safety guardrails (step limit → permission → cost cap → HITL) are checked in that exact
order — deliberately, and for a documented reason: a naive implementation might check the cost cap
*before* permission, which means an unauthorized-tool attempt that also happens to exceed the cost
cap gets mislabeled `STOPPED_COST_CAP` in the audit trail instead of `BLOCKED_PERMISSION` —
corrupting exactly the kind of anomaly-detection signal an audit trail exists to provide. See
`debug/issue-01` for the full write-up and `agent/guardrails.py`'s own docstring for the in-code
explanation.

## End-to-end verification

`scripts/verify_e2e.sh` runs `backend/verify_e2e.py` inside the live container over real HTTP (no
mocks) — including actually consuming a streamed agent run as a real client would, and actually
running a paused-for-approval run through to resumption: wait for both local models to report warm
→ signup → JWT auth → a calculator run reaching the numerically-correct answer → a direct regression
test for the guardrail-order bug pattern → a direct regression test for an
abandoned-run reaper (see `debug/issue-03`) → a real HITL pause-approve-resume flow AND a real
pause-deny-resume flow → step-limit and cost-cap guardrail stops → History semantic search → a $0
budget cap blocking the OpenRouter escalation → one real OpenRouter escalation call → admin
permission boundaries. Actual results from this build are recorded in
[`../../history/v1.0.0.md`](../../history/v1.0.0.md).

## Credit

This PoC is original work, using publicly documented model IDs, APIs, and libraries cited throughout
`docs/guide.html`. No application code was copied from another repository — though its architecture
deliberately reuses proven patterns (auth, bootstrap isolation, readiness probing, streaming SSE
infrastructure, the daily-budget-cap governance pattern) from this same project series' own
Week1-6 PoCs, and its ReAct loop design and local-agent model choice follow well-documented,
publicly available patterns for small-model ReAct agents.

## License

Portfolio PoC — see the top-level repository for licensing context. Third-party libraries/models
retain their own licenses as documented in `docs/guide.html`.
