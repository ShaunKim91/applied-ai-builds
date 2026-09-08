# Time & Cost Estimate — Building VoxIQ via Vibe Coding

This document distinguishes **measured** numbers (real data from this
actual build session) from **estimated** ones (reasoned projections,
clearly labeled) — per this project's "no hallucinated numbers" rule, we'd
rather show you the method than fabricate false precision. See
`../../week1/PoC/prompts/time_and_cost_estimate.md` for the same exercise
done for CommerceIQ, which this document deliberately mirrors.

## What was different about this build's research phase

CommerceIQ's build ran 8 parallel research sub-agents to survey standard
approaches and library/model choices for its own topic area before design
work started (documented, measured, in that project's own cost estimate).
VoxIQ's plan was built **directly on top of that already-completed
research** plus a review of CommerceIQ's own finished codebase — no fresh
multi-agent research fan-out was needed this time, because the facts a
general survey would have produced (established conventions, prior model
choices, established Docker/script patterns) were already sitting in this
same session's context and in CommerceIQ's real files. This is a genuine
efficiency gained specifically from building each product right after the
previous one in the same continuous session, not a
skipped step — see `vibe_coding_prompts.md`'s Phase 0.5 for the prompting
pattern that made this possible.

This is not instrumented with a token counter in this environment, so no
"tokens spent on research" row is given for VoxIQ the way CommerceIQ's
document has one — stating a number here without a real measurement would
violate this project's own honesty rule.

## What was actually measured in this build

| Item | Measured value |
|---|---|
| Docker image build (first time, cold cache) | full log captured; largest single layer was the Python dependency install at 289.7 s (pip installing ~90 packages including torch, transformers, sentence-transformers, chromadb, openai-whisper) |
| Bootstrap (clean-rebuild, from-zero volumes) | 274 s total for 2 datasets + 5 models — see `../history/v1.0.0.md`'s timing table for the per-step breakdown |
| End-to-end verification run (12 checks) | ~6 s total, of which the sandbox/analytics-agent check alone was 4.4–5.0 s (local LLM generation + subprocess execution) |
| OpenRouter real API call (`qwen/qwen3-8b`) | 6.3 s round-trip, measured directly against the live container |
| Real bugs found and fixed | 2 (see `../debug/`) — both found by testing the actual running app, not by static code review |
| Docker registry connectivity issue (infrastructure, not app code) | this session hit a genuine several-minutes-long Docker Desktop VM registry-pull hang before the first build could even start (unrelated to VoxIQ's code); resolved by a full Docker Desktop process restart plus retrying the pull, which succeeded on the very next attempt — not counted in the estimates below since it is a local-machine infrastructure issue, not a cost of building this specific app |

## Estimated cost for the full build (design + implementation + docs)

As with CommerceIQ, implementation + documentation token usage was **not
instrumented** in this environment, so the figures below are a **reasoned
estimate**. Method: VoxIQ reused a working template (auth, Docker,
scripts) rather than building it from scratch, which the Week1 estimate's
own Phase 4/5 implementation cost does not benefit from — so this build's
implementation-phase estimate is toward the *lower* end of a comparable
from-scratch full-stack build.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Planning (built on already-known Week1 context; no fresh research fan-out) | 0.1M – 0.3M | ≈ $0.5–2 |
| Backend + frontend implementation (partially templated from CommerceIQ) | 1.8M – 3.2M | ≈ $7–18 |
| Docker build/debug + E2E verification iteration (incl. the Docker registry troubleshooting) | 0.4M – 0.9M | ≈ $3–8 |
| Documentation (architecture.md, flowchart.md, HTML guide, this prompt set, screenshots) | 0.6M – 1.2M | ≈ $3–8 |
| **Total (estimated)** | **≈ 2.9M – 5.6M tokens** | **≈ $13 – 36** |

This is meaningfully lower than CommerceIQ's estimated $20–50 total,
consistent with the qualitative claim above: building on an
already-debugged template costs less than building the template itself.

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token
API billing**, the same framing as Week1's document applies: this is a
one-time cost per project, smaller than CommerceIQ's because more of the
underlying scaffolding was reused rather than regenerated.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Planning (reusing existing context) | ~5 min | No parallel research fan-out needed this time |
| Backend + frontend implementation | ~35–55 min | ~55 files; several (auth, security, bootstrap pattern) adapted from CommerceIQ rather than written from scratch |
| Docker image build (first time) | ~6 min | Measured: pip install of the Python dependency set was the dominant cost at 289.7 s |
| Docker registry troubleshooting (infrastructure, this session only) | ~15–20 min | A genuine, unplanned VM-level registry-pull hang — see `../debug/` note above; not representative of a typical build |
| Model + dataset warm-up (container's first boot, clean-rebuild measurement) | 274 s (measured) | 5 HuggingFace/Whisper models (~3.4 GB combined) + 2 public datasets, downloaded once, cached afterward |
| End-to-end verification run | ~6 s (measured) | All 12 checks are fast on CPU for this week's model sizes — no diffusion-scale generation step this time |
| Documentation + screenshots | ~20–30 min | Mermaid diagrams, bilingual HTML guide, 7 Playwright screenshots (one recaptured after the issue-02 fix) |
| **Total, one AI-assisted session (excluding the one-off infra troubleshooting)** | **≈ 1 – 1.5 hours** | Faster than CommerceIQ's ≈1.5–3 hours, consistent with reusing a proven template instead of building one from zero |

## Caveats

- **The Docker registry hang was a real, measured event in this specific
  session** but is explicitly excluded from the "typical build" time
  estimate above because it is a local Docker Desktop VM networking issue
  unrelated to VoxIQ's own code — including it in a general estimate would
  overstate how long this kind of build normally takes on a healthy
  connection.
- These are estimates for **one AI coding session producing one PoC**, not
  a general "AI coding costs X" claim — actual cost scales with how much
  templating is available to reuse and how much debugging a given build
  needs.
- Cloud AI usage inside the *running app itself* (the OpenRouter
  `qwen/qwen3-8b` analytics feature) is a separate, much smaller ongoing
  cost — see `docs/guide.html`'s monthly operating-cost section — and is
  unrelated to the one-time cost of building the app.
