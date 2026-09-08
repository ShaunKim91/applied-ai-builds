# Time & Cost Estimate — Building Lucent via Vibe Coding

This document distinguishes **measured** numbers (real data from this
actual build session) from **estimated** ones (reasoned projections,
clearly labeled) — per this project's "no hallucinated numbers" rule. See
the Week1-12 PoCs' own `prompts/time_and_cost_estimate.md` files for the
same exercise done for CommerceIQ, VoxIQ, and Parchment.

## What was different about this build

This round's request added real scope beyond a template reuse: genuine
token-by-token streaming (both local and cloud), a groundedness-checking
system, and a from-scratch glass design system (gradient mesh background,
new component library conventions) — none of which existed in any prior
week's code to copy. Offsetting that, the backend infrastructure (auth,
bootstrap isolation, readiness probing, the reranker model wrapper) was
reused verbatim from the Week1-12 PoCs.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build (local, before Docker) | 0 type errors, `vite build` completed in ~0.6s, ~200 KB JS bundle (~64 KB gzipped) |
| Federalist Papers essay parsing | 85 real essays extracted via structural regex parsing of the actual downloaded text (verified count, not assumed) |
| Docker image build (first time, cold cache) | see `../history/v1.0.0.md` for the full timing breakdown |
| Bootstrap (3 models + seed corpus, from-zero volumes) | see `../history/v1.0.0.md`'s timing table |
| End-to-end verification run (13 checks, incl. real streaming consumption + a real Korean-language cross-lingual query) | see `../history/v1.0.0.md` |
| Real bugs found and fixed | see `../debug/` — recorded only if genuinely encountered, never fabricated |

## Estimated cost for the full build (design + implementation + docs)

As with the prior PoCs, token usage was **not instrumented** in this
environment, so the figures below are a **reasoned estimate**. This build's
implementation scope was larger than a pure template reuse (real streaming
infrastructure, a groundedness checker, a new design system from scratch)
but smaller than a from-zero build (auth/bootstrap/readiness/reranker code
all reused verbatim) — expect it to land above VoxIQ/Parchment's estimates.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Planning (one research agent + live fact verification of the corpus/URLs + essay-count sanity check) | 0.2M – 0.4M | ≈ $1–3 |
| Backend + frontend implementation (streaming infra + groundedness checker + new design system are all genuinely new code) | 2.5M – 4.0M | ≈ $10–22 |
| Docker build/debug + E2E verification iteration (incl. real streaming-response assembly in the test script) | 0.4M – 0.9M | ≈ $3–8 |
| Documentation (architecture.md's baseline-comparison table, flowchart.md, HTML guide, this prompt set, screenshots) | 0.7M – 1.3M | ≈ $4–9 |
| **Total (estimated)** | **≈ 3.8M – 6.6M tokens** | **≈ $18 – 42** |

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token
API billing**, the same framing as the prior documents applies — a
one-time cost per project.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Planning (research agent + live verification of 2 real corpora + a structural-parsing sanity check) | ~12–18 min | New facts to verify this round: the Gutenberg URL, the Korean Wikipedia article's existence/topic match, and the essay-split regex's actual match count against the real text |
| Backend + frontend implementation (streaming infra, groundedness checker, new glass design system, 5 pages) | ~55–80 min | ~50 backend/frontend files; streaming (`TextIteratorStreamer` + SSE parsing on both ends) and a from-scratch design system both add real time a pure template reuse wouldn't need |
| Docker image build (first time) | see `../history/v1.0.0.md` | Real measured number in the build log |
| Model + seed-corpus warm-up (container's first boot) | see `../history/v1.0.0.md` | Real measured number |
| End-to-end verification run | see `../history/v1.0.0.md` | Real measured number |
| Documentation + screenshots | ~20–30 min | Mermaid diagrams, bilingual HTML guide, Playwright screenshots of streaming chat + citations UI |
| **Total, one AI-assisted session** | **≈ 1.5 – 2.2 hours** (excluding real measured Docker/verification time, added from the history log) | Somewhat more than Parchment's, consistent with this round's larger genuinely-new-code scope |

## Caveats

- These are estimates for **one AI coding session producing one PoC**, not
  a general "AI coding costs X" claim.
- Prompt caching, effort-level tuning, and batching can reduce real-world
  cost well below the naive per-token estimate above.
- Cloud AI usage inside the *running app itself* (the OpenRouter
  `qwen/qwen3-8b` chat provider) is a separate, much smaller ongoing cost —
  see `docs/guide.html`'s monthly operating-cost section — unrelated to the
  one-time cost of building the app.
