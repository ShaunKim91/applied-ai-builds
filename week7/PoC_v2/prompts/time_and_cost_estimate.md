# Time & Cost Estimate — Building Threshold via Vibe Coding

Distinguishes **measured** (real data from this build session) from **estimated** (reasoned
projections, clearly labeled) numbers, per this project's "no hallucinated numbers" rule. See
`week6/PoC_v2/prompts/time_and_cost_estimate.md` for the same exercise done for Verity, this
build's companion.

## What was different about this build

Unlike Verity (the first half of this round's rebuild, which also had to do the research/target-
setting/design-system work for the whole two-product suite), Threshold inherited an already-
established company narrative, design system, and security architecture — meaningfully reducing its
own research and design overhead. Its own genuinely new scope was narrower but still real: a
claims-processing tool set redesign (including a real engineering upgrade, amount-aware HITL), and
carrying forward six specific known bug classes from the predecessor Cradle PoC as regression tests
from day one. One new bug (in two manifestations) was found and fixed in genuinely new territory
(tool-argument parsing) neither Cradle nor Verity's own build had occasion to exercise.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build | 0 errors on the first build, ~475ms, 206 KB JS (65 KB gzipped), 14 KB CSS (3.7 KB gzipped) |
| Docker image build (clean) | 1.92 GB — see `../history/v1.0.0.md` |
| Bootstrap (2 local models, from-zero volumes, ×3) | ~11m30s–51s, consistent across all three runs |
| End-to-end verification | 26 checks, all passing on the final clean rebuild |
| Real bugs found and fixed | 1 (two manifestations) — see `../debug/`, both backed by directly-captured malformed trace text |
| Non-bug findings | 1 — rate-limiter/guardrail state carrying over across rapid repeated test invocations against the same long-lived container, resolved by a clean rebuild |

## Estimated cost for the full build

Token usage was not instrumented in this environment, so these are reasoned estimates. Lower than
Verity's own estimate — this build reused Verity's proven security/observability architecture
verbatim rather than designing it from scratch, and needed no new research phase for the company
narrative or design system.

| Phase | Estimated tokens | Estimated cost (Sonnet 5 pricing) |
|---|---:|---:|
| Design (tool-set redesign, amount-aware HITL specification) | 0.2M – 0.4M | ≈ $1–3 |
| Backend + frontend implementation (agent loop, guardrails, HITL, 7 pages, reusing Verity's security/audit/metrics infra) | 2.8M – 4.5M | ≈ $12–25 |
| Docker build/debug + E2E iteration (incl. 3 full clean rebuilds, 26-check suite, a real OpenRouter call) | 0.5M – 1.0M | ≈ $4–9 |
| Manual verification + real-bug investigation (screenshot inspection + trace analysis that found both bug manifestations) | 0.4M – 0.8M | ≈ $3–6 |
| Documentation (architecture.md, flowchart.md, guide.html, this prompt set, screenshots) | 0.6M – 1.1M | ≈ $3–8 |
| **Total (estimated)** | **≈ 4.5M – 7.8M tokens** | **≈ $23 – 51** |

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Design (tool-set redesign) | ~15–20 min | Reused Verity's company narrative/design system; the new work was specifically the claims-tool set and amount-aware HITL |
| Backend + frontend implementation | ~70–100 min | A materially large surface (agent loop, guardrails, HITL, 7 pages) but with proven security/audit/metrics infra copied, not designed fresh |
| Docker build + bootstrap (×3, incl. two clean rebuilds for the two-manifestation bug fix) | see `../history/v1.0.0.md` | Real measured numbers, consistent across all three |
| End-to-end verification (multiple runs across fixes) | see `../history/v1.0.0.md` | Real measured numbers |
| Manual verification + real-bug fixing (one bug, two manifestations, root-caused and generally fixed) | ~25–35 min | Finding the second manifestation specifically required constructing the fix's own plausible failure mode after the first one already passed its own test |
| Documentation + screenshots | ~25–35 min | Mermaid diagrams, bilingual HTML guide, 10 screenshots |
| **Total, one AI-assisted session** | **≈ 2.5 – 3.3 hours** (excluding real measured Docker/verification time, added from the history log) | Somewhat less than Verity's own estimate, reflecting the reused architecture |

## Caveats

- Estimates for **one AI coding session producing one PoC**, not a general "AI coding costs X" claim.
- Real OpenRouter calls made during development and verification were each a fraction of a cent;
  none were made silently or outside the admin-configured budget cap.
- Combined with Verity's own estimate, the full two-product Fenwick Mutual suite rebuild is
  estimated at roughly **$54–112** and **5.5–7.3 hours** of AI-assisted session time in total —
  substantially more than any single-product weekly PoC in this project series, reflecting the
  genuinely larger scope this round's request called for.
