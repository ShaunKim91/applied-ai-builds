# Vibe-Coding Prompt Playbook — VoxIQ (Week2 PoC)

This is the prompt sequence a student could actually use — with an AI coding
tool such as Claude Code — to reproduce a project like VoxIQ from scratch. It
is written from how this exact PoC was actually built in this session,
broken into the same phases as the Week1 PoC's own playbook
(`../../1st_week/PoC/prompts/vibe_coding_prompts.md`), because reusing a
proven prompt structure across weeks is itself part of what makes a second
build go faster than the first.

**Why phases, not one giant prompt**: see the Week1 playbook's own
rationale — it applies unchanged here. The one Week2-specific addition is
Phase 0.5 below: reusing a previous week's *code*, not just its prompting
pattern.

## Phase 0 — Research before touching code

> Research the standard approaches and typical library/model choices for
> these four AI techniques (tokenization/self-attention, bi-encoder vs.
> cross-encoder retrieval, Whisper/audio ASR, E2B code sandboxes). Also
> tell me what the CommerceIQ PoC in this same repo already
> established architecturally, since I want to reuse its proven template
> rather than reinvent it.

**Why this prompt first, and why the second half matters here
specifically**: by Week2, there is now a *previous PoC in the same repo*
that already solved auth, Docker port auto-detection, readiness probing,
and bootstrap isolation. Asking only about the new week's content would
have thrown that away and risked re-introducing bugs Week1 already found
and fixed.

## Phase 0.5 — Explicitly reuse a working template (Week2-specific)

> Copy CommerceIQ's proven scaffolding as the starting point for VoxIQ:
> `security.py`, the JWT/bcrypt auth router, the shape-only email validator
> (not `EmailStr` — it broke `.local` admin logins there), the `_warm_step()`
> bootstrap-isolation pattern, the readiness-probe endpoint shape, the
> multi-stage Dockerfile structure, and the setup/run/stop/verify_e2e script
> skeletons. Adapt names, ports (8730s instead of 8720s), and model lists —
> don't just reference them abstractly, actually carry the working code
> forward.

**Why this is its own phase**: "be aware of what Week1 did" and "actually
copy Week1's already-debugged code" are different instructions. The first
produces an AI that reinvents the same bugs from a vague memory of the
pattern; the second produces one that inherits the fixes for free —
confirmed in this build: the first-ever `verify_e2e.sh` run against VoxIQ
passed 12/12 with zero real bugs, unlike Week1's first pass (which needed
several debug/ fixes) — see `../history/v1.0.0.md`.

## Phase 1 — Plan before building

> Given that research, design a PoC that combines all four AI
> techniques (embeddings/reranking, audio transcription, a code
> execution sandbox, and tokenizer/attention internals) into one coherent
> product — not four unrelated demo tabs. Same non-negotiables as Week1:
> FastAPI + React/TypeScript (not Streamlit), Docker with auto-detected free
> ports and containers that are never auto-removed, SQL + vector DB, real
> public datasets with auto-download scripts, auth + admin console, at
> least 2 AI models (this project will end up with 6), and a completely
> faithful bill of materials — no fabricated URLs or license claims. Write
> the plan to a file before writing any code.

## Phase 2 — Verify facts with live tools, not memory

> Before finalizing the dataset choices: confirm the exact GitHub path for
> Whisper's own `jfk.flac` test asset, confirm the HuggingFace dataset ID
> and parquet URL for a small LibriSpeech sample set, and actually fetch 2-3
> of the Federal Reserve's FOMC-minutes URLs you're proposing to hardcode —
> don't guess the date-based URL pattern, confirm it resolves to a real page
> with real minutes text first.

**Why**: exactly the same reasoning as Week1's Phase 2 — hosting URLs and
exact paths inside someone else's GitHub repo or a government website are
not the kind of fact an LLM should assert from memory alone.

## Phase 3 — Scaffold the repo structure

> Create VoxIQ's directory scaffolding, mirroring CommerceIQ's shape:
> `backend/app/{ml,etl,routers}`, `frontend/src/{pages,components,i18n,theme,api}`,
> `docker/`, `scripts/`, `docs/screenshots/`, `data/`.

## Phase 4 — Backend, one layer at a time

> Implement in this order, pausing after each: (1) config.py + models.py —
> no hardcoded secrets, `*_api_key_file` path references only; (2) copy
> security.py + the auth router from CommerceIQ nearly as-is; (3) the six
> ml/ wrappers as lazy-loaded singletons (bi-encoder, cross-encoder, Whisper,
> local LLM, sandbox, tokenizer explorer) — the sandbox needs real OS
> resource limits (`resource.setrlimit`) and a restricted `__builtins__`
> allowlist, not just a bare `exec()`; (4) the two etl/ downloaders,
> idempotent, with the URLs verified in Phase 2; (5) the routers, each
> logging to `audit_logs`.

**Why the sandbox gets called out explicitly**: an AI asked generically to
"run generated code" will often reach for a bare `exec()` with no limits at
all — naming the specific hardening technique (resource limits + restricted
builtins + subprocess isolation + timeout) up front, and explicitly framing
it as "teaching-grade, not production," prevents both an unsafe
implementation and a false claim of real security.

## Phase 5 — Frontend, matching the API contract exactly

> Build the six pages against the routers you just wrote — read the actual
> request/response JSON, don't invent shapes. The Knowledge Search page
> specifically needs to show the bi-encoder result list and the
> cross-encoder-reranked list side-by-side, not merged into one — that
> comparison *is* the pedagogical point of showing retrieve-then-rerank
> directly. Reuse the dataviz
> skill's validated color palette for the attention heatmap.

## Phase 6 — Containerize

> Same Dockerfile/compose pattern as CommerceIQ, with one addition:
> Whisper needs the `ffmpeg` system binary — add it to the `apt-get install`
> line in the runtime stage. Keep the `TORCH_INDEX` build-arg declared in
> `docker-compose.yml`'s `build.args`, not passed ad hoc on the CLI, so cache
> hits are reliable across different invocation paths (this was a real
> Week1 finding — see CommerceIQ's `debug/issue-04`).

## Phase 7 — Prove it actually works

> Write `verify_e2e.py` covering: health → wait for all 5 local models warm
> → signup → Bearer auth → list/transcribe sample audio → transcribe an
> uploaded file → knowledge search (assert both encodings are present) →
> analytics agent (assert the generated code actually ran and produced
> stdout) → tokenizer/attention → admin boundary (403 for a regular user,
> 200 for admin). Run it against the real running container and paste back
> the actual PASS/FAIL table.

## Phase 8 — Document with facts already in hand, not invented ones

> Write architecture.md, flowchart.md, and docs/guide.html using only
> numbers and citations already established in this session — the real
> `verify_e2e.sh` output, the real OpenRouter latency you just measured, the
> real dataset licenses from Phase 2. Label anything you haven't measured
> (e.g., a production cloud cost) explicitly as an estimate.

## General prompting habits used throughout this build

- **Explicitly point at a previous week's code to reuse, not just its
  pattern in the abstract.** This was the single biggest time-saver in this
  build — see Phase 0.5.
- **Front-load constraints once, in the plan.** "5 local models, 1 opt-in
  cloud model," "ffmpeg needed for Whisper," "sandbox is teaching-grade, say
  so everywhere" were all stated up front, not patched into five files
  afterward.
- **Name exact model IDs already validated elsewhere in this project series**
  (`sentence-transformers/all-MiniLM-L6-v2`, `Qwen/Qwen2.5-0.5B-Instruct`) —
  avoids an AI substituting a plausible-sounding but different, unvalidated
  model.
- **Ask for real command output at every verification step** — the
  `verify_e2e.sh` PASS/FAIL table, the actual `docker pull` log when
  debugging a registry hang, the actual `curl` response from a live
  OpenRouter call — never a description of what output "should" look like.
