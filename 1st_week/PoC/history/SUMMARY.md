# History — Summary

**Current version: v1.0.1** (2026-08-28) — see [`v1.0.1.md`](v1.0.1.md) for the follow-up review log, and [`v1.0.0.md`](v1.0.0.md) for the original build log.

## TL;DR

CommerceIQ (PoC) went from an approved plan to a fully verified, screenshot-documented product in one continuous build, then got a follow-up security/documentation audit:

- **5 AI models wired in** (ViT-tiny, tiny-sd, multilingual-e5-small, Qwen2.5-0.5B-Instruct locally; `qwen/qwen3-8b` via OpenRouter as a validated opt-in) across 4 features (Catalog Vision, Generative Studio, Demand Forecasting, Semantic Search) plus auth and an Admin Console.
- **All 12 end-to-end checks pass** against the live Docker container over real HTTP — no mocked steps anywhere in the verification.
- **7 real issues were found and fixed** across both versions (not merely anticipated in the abstract) — see [`../debug/`](../debug/) for each one's root cause and fix. The most significant: admin login was completely broken by an over-strict email validator, a forecast accuracy metric (MAPE) could report a nonsensical 131,574.8% on real data due to $0-revenue days, and one failed dataset download could silently skip warming all 4 AI models — all three fixed with verified before/after evidence.
- **A genuine zero-state clean rebuild was proven**, not just claimed: full `docker compose down -v` + `docker rmi` + a fresh `scripts/setup.sh` run, which is also exactly what surfaced the bootstrap-isolation bug (`debug/issue-06`) via a real transient DNS failure.
- **A real API-key-leak audit** was run twice, with two independent methods, confirming the OpenRouter key exists only in its intended file — and closed a real gap found along the way (no root-level `.gitignore` protecting `api_keys/` at the whole-repo level).
- **Real, measured numbers throughout** — hardware footprint, model parameter counts, per-feature latency, and OpenRouter cost are all measured in `v1.0.0.md`, not estimated.
- **6 real screenshots**, captured by driving the actual running app with Playwright, embedded in `docs/guide.html`.

## What's next (not yet built, tracked for future versions)

- OpenAI/Claude/Gemini LLM providers are scaffolded (config fields exist) but not implemented/validated — see `backend/app/ml/llm.py`.
- Rate limiting on the generation/OpenRouter endpoints (noted as a production-deployment gap in `docs/guide.html`).
- `debug/issue-06`'s fix (isolated bootstrap steps) was verified via a clean rebuild that happened *not* to hit a second live DNS failure — the isolation logic itself was verified by code reading, not by reproducing the exact original failure a second time. See that issue's Verification section for how to test it directly if you want to.

## How to pick this back up

1. `cd 1st_week/PoC/projects/commerceiq && ./scripts/run.sh` (or `setup.sh` if starting completely fresh).
2. `./scripts/verify_e2e.sh` to confirm the baseline still holds before making changes.
3. Check `../plan/v1_plan.md` for the original approved scope, and `../debug/README.md` before touching anything the debug log already covers.
