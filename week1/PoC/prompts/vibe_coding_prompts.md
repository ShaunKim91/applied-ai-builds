# Vibe-Coding Prompt Playbook — CommerceIQ (PoC)

This is the prompt sequence a student could actually use — with an AI coding
tool such as Claude Code — to reproduce a project like CommerceIQ from
scratch. It is written from how this exact PoC was actually built in this
session, broken into the same phases, so it doubles as a "how a professional
prompts a multi-week build" reference, not just a project spec.

**Why phases, not one giant prompt**: a single "build me a full-stack AI
commerce app" prompt produces something that *looks* plausible but usually
has silently-wrong plumbing (auth, ports, model loading order) that's
expensive to debug after the fact. Splitting into research → plan → scaffold
→ backend → frontend → containerize → verify → document lets you catch a
wrong turn one phase early instead of after everything is built on top of it.

## Phase 0 — Research before touching code

> Analyze the existing reference material and prior example code in this
> repository (organized by module). For each module, summarize: the core
> topics, the exact libraries/model IDs used in the example code, what the
> reference implementation builds, and any Docker/shell-script conventions
> already established. I need this before designing a new, higher-quality
> project so it's consistent with (and can build on) what's already
> established.

**Why this prompt first**: an AI that hasn't read the existing reference
material will invent a plausible-sounding but *inconsistent* tech stack
(different port ranges, a different auth pattern, ignoring models already
validated elsewhere in this same series). Feeding it the real prior art up
front is the single highest-leverage thing you can do before design work
starts.

## Phase 1 — Plan before building

> Given that research, design a PoC that combines three AI topics (Vision
> Transformer classification, diffusion image generation, time-series
> forecasting/anomaly detection) into one coherent commercial product — not
> three unrelated demo tabs. Requirements: FastAPI +
> React/TypeScript frontend (not Streamlit — I need commercial-grade UI),
> Docker with auto-detected free ports and containers that are never
> auto-removed, SQLite + a vector store, real public datasets with
> auto-download scripts, auth + an admin console, at least 2 AI models
> (prefer local/HuggingFace, cloud API only where justified), and a
> completely faithful (no fabricated facts/URLs) bill of materials. Write the
> plan to a file before writing any code.

**Why**: locking scope and factual claims (dataset URLs, license terms,
model IDs, pricing) into a written plan *before* code generation starts
means you can fact-check them once, cheaply, instead of discovering a
hallucinated dataset URL three files deep into implementation.

## Phase 2 — Verify facts with live tools, not memory

> Before finalizing the dataset and model choices in the plan: web-search
> the current OpenRouter pricing/model catalog for a cheap Qwen3 model, fetch
> the UCI Online Retail dataset page for its real direct-download URL and
> license, and fetch the GitHub repo for the sample images you're proposing
> to confirm the exact file paths and license. Update the plan with what you
> actually found, not what you assume.

**Why**: model catalogs, prices, and dataset hosting URLs change; an LLM's
training-time memory of them is frequently stale or subtly wrong (a renamed
file, a changed price tier). This is the step that prevents "the shell
script 404s on line 1 of a fresh clone."

## Phase 3 — Scaffold the repo structure

> Create the directory scaffolding for the project: backend/app (with ml/,
> etl/, routers/ subpackages), frontend/src (pages/, components/, i18n/,
> theme/, api/), docker/, scripts/, docs/screenshots/, data/. Don't write
> business logic yet — just the structure and empty/`__init__.py` files.

## Phase 4 — Backend, one layer at a time

> Implement the backend in this order and stop after each so I can sanity
> check it: (1) config.py + database.py + models.py (SQLAlchemy ORM) — no
> secrets hardcoded, API keys read from files at call-time; (2) security.py
> (JWT + bcrypt, supporting both cookie and Bearer auth so both a browser and
> a script can authenticate); (3) the five ml/ wrappers as lazy-loaded
> singletons (vision, diffusion, embeddings, local LLM, forecast) — each
> needs a `model_info()` that proves it's really loaded, not mocked; (4) the
> two etl/ scripts that download the public datasets, idempotently, with
> license/citation comments; (5) the routers, one feature at a time, each
> writing to both the SQL tables and (where relevant) the vector store, and
> logging every AI call to an audit_logs table.

**Why one layer at a time**: reviewing a 2,000-line diff for correctness is
much harder than reviewing 150 lines five times — errors get caught (and
are cheap to fix) before the next layer builds on top of a wrong one.

## Phase 5 — Frontend, matching the API contract exactly

> Now build the React/TypeScript frontend against the API you just wrote —
> don't invent endpoint shapes, read the router files for the exact request/
> response JSON. Use the validated color/spacing palette conventions from
> [design-system reference] for the chart and cards, not ad-hoc colors.
> Support English (default) + Korean via a simple i18n context, and a light
> (default) + dark theme toggle, both persisted to localStorage.

## Phase 6 — Containerize

> Write a multi-stage Dockerfile (Node build stage → Python-only runtime
> stage) and docker-compose.yml. The container must never be silently
> deleted (use `stop`, not `down`, in the convenience scripts), must
> auto-detect the host's GPU and choose the matching torch wheel, must
> auto-select a free host port (write a small portable /dev/tcp-based bash
> port scanner, not a tool that might not exist on Windows Git Bash), and
> must download models/datasets into named volumes on first boot so restarts
> don't re-download anything. Then write setup.sh / run.sh / stop.sh /
> verify_e2e.sh wrapping it.

## Phase 7 — Prove it actually works

> Write an end-to-end verification script that runs *inside* the container
> over real HTTP — no mocking — exercising every feature: signup, both
> classification paths, submitting and polling a real generation job,
> running a real forecast (assert the AI insight text is non-empty), a real
> semantic search, and confirming a regular user is correctly 403'd from
> admin endpoints while an admin isn't. Run it against the actual running
> container and show me the real PASS/FAIL output — don't summarize what it
> *should* show.

**Why this is its own phase, not folded into Phase 4**: "the code compiles"
and "the code is actually correct end-to-end, in a container, on real data"
are different claims. Insisting on the second, with a real run and real
output pasted back, is what turns "should work" into "does work."

## Phase 8 — Document with facts already in hand, not invented ones

> Now write architecture.md and flowchart.md (Mermaid diagrams matching the
> real function names), then the bilingual HTML operations guide — but only
> using facts we've already established (measured hardware numbers from the
> actual build/run, the actual dataset citations from Phase 2, actual
> screenshots from the running app). Where you don't have a measured number
> (e.g. a production cloud cost estimate), say so explicitly and label it as
> an estimate with its assumptions, rather than presenting it as measured.

## General prompting habits used throughout this build

- **Front-load constraints, don't discover them mid-build.** "16GB RAM
  target," "OpenRouter only this round," "reference the key file, never
  hardcode it" were all stated once, up front, in the plan — not corrected
  after the fact in five different files.
- **Ask for the plan file, then approve it, before code.** Cheap to redirect
  a plan; expensive to redirect a half-built app.
- **Name the exact model IDs and versions you want reused**, especially ones
  already validated elsewhere in the same codebase (`WinKawaks/vit-tiny-patch16-224`,
  `segmind/tiny-sd`) — this avoids the AI picking a plausible-sounding but
  different model that then needs separate validation.
- **Ask for real command output, not a description of expected output**,
  whenever a claim ("the tests pass," "the container is healthy") can be
  checked by actually running something.
