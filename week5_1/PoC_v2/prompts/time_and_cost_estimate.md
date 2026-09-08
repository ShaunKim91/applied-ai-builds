# Time & Cost Estimate — Building Verity via Vibe Coding

Distinguishes **measured** (real data from this build session) from **estimated** (reasoned
projections, clearly labeled) numbers, per this project's "no hallucinated numbers" rule.

## What was different about this build

This wasn't an incremental weekly build — it was a full rebuild triggered by structural feedback
("no prior week states a clear target; raise the bar to commercial-grade"), which meant: research
into what was actually missing across six prior PoCs, designing a new company/persona/product-suite
narrative from scratch, AND implementing a materially larger security/observability surface
(rotating auth, CSRF, lockout, a hash-chained audit log, rate limiting, real metrics) than any prior
PoC in this project series attempted. Offsetting that: the core research/grounding/streaming
infrastructure pattern was already well-proven from five prior builds and didn't need to be
reinvented, just re-implemented with new business logic.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Frontend TypeScript build | 0 errors on the first build, ~460ms, 210 KB JS (66 KB gzipped), 14 KB CSS (3.8 KB gzipped) |
| Docker image build (clean) | 1.95 GB — see `../history/v1.0.0.md` |
| Bootstrap (3 local models, from-zero volumes) | 12m 45s, consistent with the historical Compass baseline for the same model set |
| End-to-end verification | 25 checks, all passing on the final clean rebuild — see `../history/v1.0.0.md` |
| Real bugs found and fixed | 3 — see `../debug/`, each backed by directly-measured evidence (real cosine-similarity scores, a real captured hallucinated sentence) |
| Non-bug test-tooling findings | 2 — a Playwright actionability quirk and a streaming-response wait-condition trap, both diagnosed to their actual mechanism rather than patched around |

## Estimated cost for the full build

Token usage was not instrumented in this environment, so these are reasoned estimates. This build's
scope is larger than a typical incremental weekly PoC: a full research phase (auditing six prior
PoCs' positioning, designing a two-product company narrative), a materially larger security/
observability implementation, and a research phase specifically for verifying the two real
grounding/fraud-detection gaps found via measurement rather than assumption.

| Phase | Estimated tokens | Estimated cost (Sonnet 5 pricing) |
|---|---:|---:|
| Research (auditing prior PoCs' positioning, prior-work re-verification, target/design planning via subagents) | 0.5M – 0.9M | ≈ $3–6 |
| Backend + frontend implementation (org model, auth hardening, hash-chained audit log, rate limiting, metrics, 8 pages, fictional corpus) | 3.5M – 5.5M | ≈ $16–30 |
| Docker build/debug + E2E iteration (incl. 2 full clean rebuilds, 25-check suite, a real OpenRouter call and a real live-web call) | 0.6M – 1.1M | ≈ $5–10 |
| Manual verification + real-bug investigation (screenshot inspection, direct model measurement that found the two most serious findings) | 0.5M – 0.9M | ≈ $3–6 |
| Documentation (architecture.md, flowchart.md, guide.html, this prompt set, screenshots) | 0.7M – 1.3M | ≈ $4–9 |
| **Total (estimated)** | **≈ 5.8M – 9.7M tokens** | **≈ $31 – 61** |

Higher than a typical single-product weekly build — this round was, in substance, closer to two
builds' worth of design work (company + persona + shared design system) compressed into the first
product's implementation, plus a meaningfully larger security surface.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Research + target/design planning | ~25–35 min | Auditing 6 prior PoCs, re-verifying prior-project facts, designing a two-product shared narrative via a dedicated planning pass |
| Backend + frontend implementation | ~90–130 min | A materially larger surface than a typical week: org model, rotating auth, CSRF, lockout, hash-chained audit, rate limiting, metrics, 8 pages, a hand-authored fictional corpus |
| Docker build + bootstrap (×2, incl. the final clean rebuild) | see `../history/v1.0.0.md` | Real measured numbers, consistent across builds |
| End-to-end verification (×3 runs across fixes) | see `../history/v1.0.0.md` | Real measured numbers |
| Manual verification + real-bug fixing (3 real bugs, root-caused and fixed, not just noted) | ~30–40 min | Directly measuring embedding similarity scores and reproducing a hallucinated entity by hand, not just spot-checking |
| Documentation + screenshots | ~30–40 min | Mermaid diagrams, bilingual HTML guide, 11 screenshots |
| **Total, one AI-assisted session** | **≈ 3.0 – 4.0 hours** (excluding real measured Docker/verification time, added from the history log) | Meaningfully more than a typical single-week build, reflecting the dual scope (research/design + a larger engineering surface) |

## Caveats

- Estimates for **one AI coding session producing one PoC**, not a general "AI coding costs X" claim.
- Real OpenRouter/live-web calls made during development and verification were each a fraction of a
  cent; none were made silently or outside the admin-configured budget cap.
