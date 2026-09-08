# Time & Cost Estimate — Building Cradle via Vibe Coding

This document distinguishes **measured** numbers (real data from this actual build session) from
**estimated** ones (reasoned projections, clearly labeled) — per this project's "no hallucinated
numbers" rule. See the Week1-5_1 PoCs' own `prompts/time_and_cost_estimate.md` files for the same
exercise done for CommerceIQ, VoxIQ, Parchment, Lucent, and Compass.

## What was different about this build

This round's request added an explicit, qualitative design bar ("genuine 3D and spatial depth, high
lightness/low saturation pastel, not a simply-made UI") on top of genuinely new technical scope: a
resumable, DB-persisted agent loop (the first PoC in this series where one logical operation can span
two unrelated HTTP requests, arbitrarily far apart in time), a real Human-in-the-Loop pause/resume
execution path, and a proactively-avoided guardrail-ordering pitfall identified during design.
Offsetting that, the backend infrastructure (auth, bootstrap isolation, readiness
probing, the embedding module, the streaming SSE plumbing, the daily-budget-cap governance pattern)
was reused verbatim from the Week2-5_1 PoCs, and this week needed no live-external-dependency
failure-handling design (Compass's `ddgs`+mock layer has no equivalent here).

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build (local, before Docker) | 0 type errors, `vite build` completed in ~630ms, ~205 KB JS bundle (~65 KB gzipped), ~17 KB CSS (~4.4 KB gzipped) |
| Docker image build (clean, from-zero) | 2.28 GB, identical across 3 separate builds — see `../history/v1.0.0.md` |
| Bootstrap (2 local models, from-zero volumes, measured 3 times) | ~11m20s–23s each time — see `../history/v1.0.0.md`'s timing table |
| End-to-end verification (16 checks, incl. a real OpenRouter escalation call, a $0-budget-cap governance test, two guardrail-order/stale-run regression tests, and a real HITL approve+deny flow) | run 4 times, 16/16 on the final run — see `../history/v1.0.0.md` |
| Real bugs found and fixed | 6 — see `../debug/` (recorded only because genuinely encountered, never fabricated; two corrected proactively before shipping, four found via manual testing/inspection) |
| Non-bug ambiguities found and fixed in the *test tooling itself* (Playwright selector/wait-condition precision) | 3 — documented in `../debug/README.md` and `prompts/vibe_coding_prompts.md` Phase 5/7, kept separate from product bugs since none affected real users |

## Estimated cost for the full build (design + implementation + docs)

As with the prior PoCs, token usage was **not instrumented** in this environment, so the figures
below are a **reasoned estimate**. This build's scope (a resumable-generator architecture, a real
HITL pause/resume path, a proactively-avoided guardrail-ordering pitfall, a from-scratch
claymorphism design system with real pointer-reactive 3D) is comparable to Compass's, with the
external-dependency-handling design traded for the new resumability/HITL architecture.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Planning (design-research agent + tracing the guardrail-order pitfall by hand) | 0.2M – 0.4M | ≈ $1–3 |
| Backend + frontend implementation (resumable agent loop, guardrails, HITL queue, claymorphism design system incl. a real 3D tilt component, 5 pages) | 3.0M – 4.8M | ≈ $13–27 |
| Docker build/debug + E2E verification iteration (incl. 3 full clean rebuilds, 4 E2E runs, and one real external rate-limit retry) | 0.5M – 1.0M | ≈ $4–9 |
| Manual verification + bug-finding (screenshot inspection that surfaced 4 of the 6 real bugs, plus fixing and re-verifying each) | 0.4M – 0.8M | ≈ $3–7 |
| Documentation (architecture.md's baseline-comparison table, flowchart.md, HTML guide, this prompt set, screenshots) | 0.7M – 1.3M | ≈ $4–9 |
| **Total (estimated)** | **≈ 4.8M – 8.3M tokens** | **≈ $25 – 55** |

Somewhat higher than Compass's estimate — the extra manual-verification phase (visually comparing
screenshots and reading raw audit-log entries, which is precisely how 4 of the 6 real bugs were
found) is genuinely additional work this build did that a purely automated-test-driven build would
not have surfaced.

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token API billing**, the same
framing as the prior documents applies — a one-time cost per project.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Planning (research agent + hand-verifying the guardrail-order pitfall) | ~15–20 min | Confirming a claimed behavior by tracing the exact scenario by hand, not just trusting a citation |
| Backend + frontend implementation (resumable loop, guardrails, HITL, claymorphism design system, 5 pages) | ~70–100 min | A new architectural pattern (the shared-generator resumable loop) and a real pointer-reactive 3D component both add genuine implementation time over a pure template reuse |
| Docker image build (first time) + 2 additional clean rebuilds for regression fixes | see `../history/v1.0.0.md` | Real measured numbers; 3 total clean rebuilds this session, each triggered by a genuine code fix worth re-verifying from zero |
| Model warm-up (each container boot) | see `../history/v1.0.0.md` | Real measured number, consistent across all 3 clean rebuilds |
| End-to-end verification runs (×4, incl. one real external rate-limit retry) | see `../history/v1.0.0.md` | Real measured numbers |
| Manual verification (screenshot comparison, direct audit-log queries) that surfaced 4 of the 6 real bugs | ~20–30 min | Genuinely additional time this build spent beyond what a "run the E2E suite once and stop" approach would have taken |
| Documentation + screenshots | ~25–35 min | Mermaid diagrams, bilingual HTML guide, Playwright screenshots of the streaming console, HITL approval flow, and dark-mode variant |
| **Total, one AI-assisted session** | **≈ 2.2 – 3.0 hours** (excluding real measured Docker/verification time, added from the history log) | Higher than Compass's, reflecting the added manual-verification time that specifically paid for itself in bugs found |

## Caveats

- These are estimates for **one AI coding session producing one PoC**, not a general "AI coding
  costs X" claim.
- Prompt caching, effort-level tuning, and batching can reduce real-world cost well below the naive
  per-token estimate above.
- Cloud AI usage inside the *running app itself* (OpenRouter's escalation calls) is a separate, much
  smaller ongoing cost — see `docs/guide.html`'s monthly operating-cost section — unrelated to the
  one-time cost of building the app. This build made several real, deliberate OpenRouter calls during
  development and verification (each a fraction of a cent); none were made silently or outside the
  admin-configured budget cap, and one hit a real, transient rate limit that was reported honestly
  rather than hidden.
