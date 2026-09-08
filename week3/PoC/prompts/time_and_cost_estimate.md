# Time & Cost Estimate — Building Parchment via Vibe Coding

This document distinguishes **measured** numbers (real data from this
actual build session) from **estimated** ones (reasoned projections,
clearly labeled) — per this project's "no hallucinated numbers" rule. See
`../../week1/PoC/prompts/time_and_cost_estimate.md` and
`../../week2/PoC/prompts/time_and_cost_estimate.md` for the same exercise
done for CommerceIQ and VoxIQ.

## What was different about this build

Like the Week2 PoC, this build's planning phase reused already-established
context (this session's own accumulated knowledge of the Week1/2 PoCs'
patterns) rather than running a fresh multi-agent research fan-out — a
single research agent surveyed the target technique set (image/multimodal
extraction, PDF parsing/summarization, HTML table scraping), which was
enough given the prior weeks' architecture was already proven. The one genuinely new research cost this round was verifying the
new model choices (SmolVLM-256M, distilbart-cnn-12-6) and the new sample
data sources (Fed PDF report, Wikipedia table) actually exist and match
their claimed specs before committing to them in the plan.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build (local, before Docker) | 0 type errors, `vite build` completed in ~0.5s, ~201 KB JS bundle (63 KB gzipped) |
| Docker image build (first time, cold cache) | see `../history/v1.0.0.md` for the full timing breakdown |
| Bootstrap (5 models + sample data, from-zero volumes) | see `../history/v1.0.0.md`'s timing table |
| End-to-end verification run (13 checks) | see `../history/v1.0.0.md` |
| Real bugs found and fixed | see `../debug/` — recorded only if genuinely encountered, never fabricated |

## Estimated cost for the full build (design + implementation + docs)

As with the Week1/2 PoCs, token usage was **not instrumented** in this
environment, so the figures below are a **reasoned estimate**. This build
had more infrastructure to reuse verbatim than VoxIQ did (Week2 itself
reused Week1's patterns; this build reused both weeks' proven auth/
bootstrap/readiness code plus two of Week2's ML wrappers directly), but
also had a genuinely new visual-design pass (new Tailwind tokens, new font
pairing, new layout) that the prior two builds didn't need — those two
factors roughly offset each other in scope.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Planning (one research agent + live fact verification, no fresh multi-agent fan-out) | 0.2M – 0.4M | ≈ $1–3 |
| Backend + frontend implementation (partially templated, plus a full new design-token pass) | 2.0M – 3.5M | ≈ $8–20 |
| Docker build/debug + E2E verification iteration | 0.4M – 0.9M | ≈ $3–8 |
| Documentation (architecture.md, flowchart.md, HTML guide, this prompt set, screenshots) | 0.6M – 1.2M | ≈ $3–8 |
| **Total (estimated)** | **≈ 3.2M – 6.0M tokens** | **≈ $15 – 39** |

Broadly comparable to VoxIQ's estimated $13–36 — the extra design-system
work is offset by the extra code reuse, as expected for a third build in
the same continuous session.

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token
API billing**, the same framing as the prior two documents applies: a
one-time cost per project, not materially larger than the previous week's
despite the new visual-design effort.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Planning (reusing existing context + live verification of 2 new models + 2 new data sources) | ~10–15 min | Slightly more than VoxIQ's, since 4 new facts needed live verification instead of reusing already-verified ones |
| Backend + frontend implementation (incl. the new design-token pass) | ~45–65 min | ~50 backend/frontend files; the new Tailwind/CSS design pass adds time a pure template-reuse build wouldn't need |
| Docker image build (first time) | see `../history/v1.0.0.md` | Real measured number in the build log |
| Model + sample-data warm-up (container's first boot) | see `../history/v1.0.0.md` | Real measured number |
| End-to-end verification run | see `../history/v1.0.0.md` | Real measured number |
| Documentation + screenshots | ~20–30 min | Mermaid diagrams, bilingual HTML guide, Playwright screenshots of a genuinely new UI |
| **Total, one AI-assisted session** | **≈ 1.5 – 2 hours** (excluding real measured Docker/verification time, added from the history log) | Comparable to VoxIQ's, since the new design work and the extra code reuse roughly cancel out |

## Caveats

- These are estimates for **one AI coding session producing one PoC**, not
  a general "AI coding costs X" claim.
- Prompt caching, effort-level tuning, and batching can reduce real-world
  cost well below the naive per-token estimate above.
- Cloud AI usage inside the *running app itself* (the OpenRouter
  `qwen/qwen3-8b` summarization feature) is a separate, much smaller
  ongoing cost — see `docs/guide.html`'s monthly operating-cost section —
  unrelated to the one-time cost of building the app.
