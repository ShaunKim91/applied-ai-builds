# Time & Cost Estimate — Building Throughline via Vibe Coding

Distinguishes **measured** (real data from this build session) from **estimated** (reasoned
projections, clearly labeled) numbers, per this project's "no hallucinated numbers" rule. See
`6th_week/PoC_v2/prompts/time_and_cost_estimate.md` and
`7th_week/PoC_v2/prompts/time_and_cost_estimate.md` for the same exercise done for Verity and
Threshold, this build's two companions.

## What was different about this build

Unlike Verity (which did the research/target-setting/design-system work for the whole suite) and
Threshold (which inherited that work but still ported an existing tool-loop mechanism), Throughline
both inherited an established company narrative/design system AND had to design a genuinely new
mechanism from scratch — real LCEL composition, dual-strategy persisted memory, structured extraction
with a conflict guardrail — none of which either sibling product's own architecture provided a
template for. This build also included real verification work with no precedent in this project series:
installing and directly testing `langchain-core`'s actual current API before writing code against it
(catching a real deprecation), and empirically testing the local model's actual multi-turn behavior in
a scratch environment before finalizing prompts, rather than reusing a sibling product's already-
validated (but differently-shaped) fix.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build | 0 errors on the first build, ~511ms, 206 KB JS (65 KB gzipped), 13.6 KB CSS (3.7 KB gzipped) |
| Docker image build (clean) | 2.09 GB — see `../history/v1.0.0.md` |
| Bootstrap (2 local models, from-zero volumes, ×3) | ~51s–55s, consistent across all three runs |
| End-to-end verification | 31 checks, all passing on two separate clean rebuilds in a row |
| Real bugs found and fixed | 4 — see `../debug/`, each backed by a directly-captured traceback or a directly-observed incorrect behavior |
| Non-bug findings | 1 — a local (non-Docker) macOS/MPS torch-backend artifact during fast-iteration development, resolved by confirming the real Docker container (CPU-only torch) never exhibited it across three clean rebuilds |

## Estimated cost for the full build

Token usage was not instrumented in this environment, so these are reasoned estimates. Higher than
Threshold's own estimate despite reusing the same security architecture — this build's own new
mechanism (LCEL chains, dual-strategy memory, the conflict guardrail) was designed from scratch, and a
meaningful share of the session went to direct empirical verification (installing real packages,
downloading and running the real local model in a scratch environment, testing real multi-turn
conversations) rather than implementation alone.

| Phase | Estimated tokens | Estimated cost (Sonnet 5 pricing) |
|---|---:|---:|
| Research + design (project-series grounding, prior-identity/pattern survey, design validation pass) | 0.5M – 0.9M | ≈ $3–6 |
| Empirical verification (real `langchain-core` API checks, real local-model behavior testing, real router-reliability measurement) | 0.6M – 1.1M | ≈ $4–8 |
| Backend + frontend implementation (chains/, models, 5 tools, routers, 6 React pages, reusing Verity/Threshold's security/audit/metrics infra) | 3.0M – 4.8M | ≈ $13–27 |
| Docker build/debug + E2E iteration (incl. 3 full clean rebuilds, 31-check suite twice, a real OpenRouter call) | 0.6M – 1.1M | ≈ $5–10 |
| Manual verification + real-bug investigation (4 bugs found via direct multi-turn testing) | 0.5M – 0.9M | ≈ $4–7 |
| Documentation (architecture.md, flowchart.md, guide.html, this prompt set, screenshots) | 0.6M – 1.1M | ≈ $3–8 |
| **Total (estimated)** | **≈ 5.8M – 9.9M tokens** | **≈ $32 – 66** |

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Research + design | ~20–30 min | Reused Verity/Threshold's company narrative/design system; new work was the mechanism design itself (LCEL chains, memory strategy, the conflict guardrail) |
| Empirical verification | ~25–35 min | Installing `langchain-core`/`torch`/`transformers` in a scratch environment, downloading the real local model, and running real multi-turn test conversations before writing product code |
| Backend + frontend implementation | ~90–120 min | The largest genuinely new surface of any product in this suite (5 new chain modules, 9 new tables, 6 React pages) |
| Docker build + bootstrap (×3, incl. two clean rebuilds for screenshot/demo-data preparation) | see `../history/v1.0.0.md` | Real measured numbers, consistent across all three |
| End-to-end verification (2 full runs on clean rebuilds) | see `../history/v1.0.0.md` | Real measured numbers |
| Manual verification + real-bug fixing (4 bugs, each found via direct multi-turn testing and fixed with a general, not narrow, solution) | ~35–50 min | Two of the four (the fact-injection gap, the LCEL composition crash) required deliberately testing scenarios the plan itself hadn't specifically called out — window overflow, cross-session conflict resolution |
| Documentation + screenshots | ~30–40 min | Mermaid diagrams, bilingual HTML guide, 9 screenshots including an organically-produced memory-conflict state |
| **Total, one AI-assisted session** | **≈ 3.3 – 4.5 hours** (excluding real measured Docker/verification time, added from the history log) | The longest of the three products in this round, reflecting the largest genuinely new mechanism design |

## Caveats

- Estimates for **one AI coding session producing one PoC**, not a general "AI coding costs X" claim.
- Real OpenRouter calls made during development and verification were each a fraction of a cent; none
  were made silently or outside the admin-configured budget cap.
- Combined with Verity's and Threshold's own estimates, the full three-product Fenwick Mutual suite
  rebuild is estimated at roughly **$86–178** and **8.8–11.8 hours** of AI-assisted session time in
  total — the largest single-round scope in this project series, reflecting the user's explicit request to
  rebuild two (in practice, given the natural three-pillar split, three) products to a materially
  higher, commercial-grade bar in one continuous round.
