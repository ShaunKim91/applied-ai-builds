# History — Summary

**Current version: v1.0.0** (2026-08-28) — see [`v1.0.0.md`](v1.0.0.md) for the full build log.

## TL;DR

VoxIQ (Week2 PoC) went from an approved plan to a fully verified,
screenshot-documented product in one continuous build, deliberately reusing
the Week1 PoC's ("CommerceIQ") already-hardened template:

- **6 AI models wired in** (bi-encoder, cross-encoder, Whisper, local
  Qwen2.5-0.5B locally; GPT-2 for tokenizer/attention; `qwen/qwen3-8b` via
  OpenRouter as a validated opt-in) across 4 features (Meeting
  Transcription, Knowledge Search, Analytics Agent, Tokenizer & Attention
  Explorer) plus auth and an Admin Console.
- **All 12 end-to-end checks pass** against the live Docker container over
  real HTTP — no mocked steps anywhere — both before and after the clean
  rebuild.
- **2 real issues found and fixed**, both genuinely encountered, not
  anticipated in the abstract: a stale "4 models" string left over from
  copy-adapting CommerceIQ's `setup.sh`, and — found by reading a
  documentation screenshot — the local 0.5B code-gen model reliably
  crashing on a data-shape assumption that the larger OpenRouter model
  handled correctly. See [`../debug/`](../debug/) for both.
- **Meaningfully fewer issues than Week1's 7** — by design: reusing
  CommerceIQ's already-debugged auth, bootstrap-isolation, and
  readiness-probe code from day one meant those bug classes had no chance
  to reappear.
- **A genuine zero-state clean rebuild was proven**: `docker compose down
  -v` + `docker rmi` + a fresh `scripts/setup.sh`, with real from-scratch
  bootstrap timing measured (274 s for all 5 models + both datasets) and
  `verify_e2e.sh` passing 12/12 immediately after.
- **OpenRouter validated with a real key and a real call** — measured 6.3 s
  latency for `qwen/qwen3-8b` generating and successfully running Python
  code against the sandbox.
- **A real, double-method API-key-leak audit** (wrapped `grep` +
  ground-truth `command grep`) found zero occurrences of the real key
  anywhere in the project tree.
- **Real, measured numbers throughout** — hardware footprint, bootstrap
  timing, per-feature latency, and OpenRouter cost/latency are all measured
  in `v1.0.0.md`, not estimated.
- **7 real screenshots**, captured by driving the actual running app with
  Playwright, embedded in `docs/guide.html`.

## What's next (not yet built, tracked for future versions)

- OpenAI/Claude/Gemini LLM providers and E2B are scaffolded (config fields
  exist) but not implemented/validated — see `backend/app/ml/llm.py` and
  `backend/app/ml/sandbox.py`.
- The local code sandbox is explicitly a teaching-grade isolation boundary,
  not a production one — see `docs/guide.html`'s limitations section for
  what a real deployment needs instead (E2B or equivalent).
- Rate limiting on the generation/OpenRouter endpoints (noted as a
  production-deployment gap in `docs/guide.html`, same as Week1).

## How to pick this back up

1. `cd week2/PoC/projects/voxiq && ./scripts/run.sh` (or `setup.sh` if
   starting completely fresh).
2. `./scripts/verify_e2e.sh` to confirm the baseline still holds before
   making changes.
3. Check `../plan/v1_plan.md` for the original approved scope, and
   `../debug/README.md` before touching anything the debug log already
   covers.
