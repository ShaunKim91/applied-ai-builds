# Time & Cost Estimate — Building Compass via Vibe Coding

This document distinguishes **measured** numbers (real data from this actual build session) from
**estimated** ones (reasoned projections, clearly labeled) — per this project's "no hallucinated
numbers" rule. See the Week1-13 PoCs' own `prompts/time_and_cost_estimate.md` files for the same
exercise done for CommerceIQ, VoxIQ, Parchment, and Lucent.

## What was different about this build

This round's request added an explicit, standing quality bar ("keep raising UI/UX and overall
quality every week") on top of genuinely new technical scope: a live, unreliable external search
dependency with its own failure-handling design (`ddgs` + mock fallback), a from-scratch
navy/brass/teal design system with a first-time dark-default and a real motion system (radar-sweep,
skeleton shimmer), a second distinct use of the OpenRouter API (its managed web-search plugin, a
different request/response shape than plain chat completions), and a cost-governance feature with
no precedent in any prior week's PoC. Offsetting that, the backend infrastructure (auth, bootstrap
isolation, readiness probing, the reranker/embedding/groundedness modules, the streaming SSE
plumbing) was reused verbatim from the Week2-13 PoCs.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build (local, before Docker) | 0 type errors, `vite build` completed in ~0.48s, ~212 KB JS bundle (~66 KB gzipped), ~17 KB CSS (~4.4 KB gzipped) |
| Docker image build (clean, from-zero) | see `../history/v1.0.0.md` for the full timing breakdown |
| Bootstrap (3 local models + a live web-search connectivity check, from-zero volumes) | see `../history/v1.0.0.md`'s timing table |
| End-to-end verification (16 checks, incl. a real OpenRouter web-search call, a $0-budget-cap governance test, and two deterministic regression tests for real previously-observed bugs) | see `../history/v1.0.0.md` |
| Real bugs found and fixed | 1 — see `../debug/` (recorded only because genuinely encountered, never fabricated) |
| Non-bug ambiguities found and fixed in the *test tooling itself* (Playwright selector precision) | 2 — documented in `../debug/README.md` and `prompts/vibe_coding_prompts.md` Phase 5, kept separate from product bugs since neither affected real users |

## Estimated cost for the full build (design + implementation + docs)

As with the prior PoCs, token usage was **not instrumented** in this environment, so the figures
below are a **reasoned estimate**. This build's scope (a new external-dependency failure-handling
design, a from-scratch design system with a real motion layer, a second distinct OpenRouter
integration shape, a cost-governance feature) is comparable to or slightly larger than Lucent's.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Planning (research agent + live verification of `ddgs` and OpenRouter's web-search plugin) | 0.2M – 0.4M | ≈ $1–3 |
| Backend + frontend implementation (search+fallback layer, ghost-citation checker, cost governance, new design system, 6 pages) | 2.8M – 4.5M | ≈ $12–25 |
| Docker build/debug + E2E verification iteration (incl. a real-money OpenRouter call and a deterministic regression test for a live-model output quirk) | 0.4M – 0.9M | ≈ $3–8 |
| Documentation (architecture.md's baseline-comparison table, flowchart.md, HTML guide, this prompt set, screenshots) | 0.7M – 1.3M | ≈ $4–9 |
| **Total (estimated)** | **≈ 4.1M – 7.1M tokens** | **≈ $20 – 45** |

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token API billing**, the same
framing as the prior documents applies — a one-time cost per project.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Planning (research agent + live verification of `ddgs`'s API surface and OpenRouter's web-search plugin's exact request shape) | ~15–20 min | New facts to verify this round: a keyless search library's current package name/API, and a specific vendor feature's exact plugin syntax and pricing |
| Backend + frontend implementation (search+fallback layer, ghost-citation checker, cost governance, new design system, 6 pages) | ~60–90 min | ~55 backend/frontend files; a from-scratch design system with a real motion layer and a first-time dark-default theme both add real time over a pure template reuse |
| Docker image build (first time) | see `../history/v1.0.0.md` | Real measured number in the build log |
| Model warm-up (container's first boot) | see `../history/v1.0.0.md` | Real measured number |
| End-to-end verification run | see `../history/v1.0.0.md` | Real measured number |
| Documentation + screenshots (incl. debugging two Playwright selector ambiguities) | ~25–35 min | Mermaid diagrams, bilingual HTML guide, Playwright screenshots of the streaming research UI, Grounding Lab, and Trend Radar |
| **Total, one AI-assisted session** | **≈ 1.7 – 2.4 hours** (excluding real measured Docker/verification time, added from the history log) | Comparable to or slightly more than Lucent's, consistent with this round's added external-dependency and cost-governance scope |

## Caveats

- These are estimates for **one AI coding session producing one PoC**, not a general "AI coding
  costs X" claim.
- Prompt caching, effort-level tuning, and batching can reduce real-world cost well below the naive
  per-token estimate above.
- Cloud AI usage inside the *running app itself* (OpenRouter's chat-completion and web-search-plugin
  calls) is a separate, much smaller ongoing cost — see `docs/guide.html`'s monthly operating-cost
  section — unrelated to the one-time cost of building the app. This build made several real,
  deliberate OpenRouter calls during development and verification (each a few cents at most); none
  were made silently or outside the admin-configured budget cap.
