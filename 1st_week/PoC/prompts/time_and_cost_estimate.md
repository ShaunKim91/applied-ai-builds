# Time & Cost Estimate — Building CommerceIQ via Vibe Coding

This document distinguishes **measured** numbers (real data from this
actual build session) from **estimated** ones (reasoned projections,
clearly labeled) — per this project's "no hallucinated numbers" rule, we'd
rather show you the method than fabricate false precision.

## What was actually measured in this build

The research phase of this build (Phase 0 in [`vibe_coding_prompts.md`](vibe_coding_prompts.md)) used 8 parallel sub-agents to read every prior module's reference material end-to-end before any design work started. Their real, logged token usage:

| Research agent | Tokens (measured) | Wall-clock duration |
|---|---:|---:|
| Module 1 deep-dive | 258,748 | 152s |
| Module 2 deep-dive | 269,414 | 168s |
| Module 3 deep-dive | 177,519 | 129s |
| Module 4 deep-dive | 192,117 | 156s |
| Module 5a deep-dive | 188,479 | 158s |
| Module 5b + Module 6 deep-dive | 383,191 | 243s |
| Earlier-modules survey | 189,441 | 154s |
| Reference-skills (3 skills) deep-dive | 129,928 | 135s |
| **Total (research phase)** | **1,788,837** | **~4 min wall-clock** (ran in parallel — wall time ≈ the slowest agent, not the sum) |

**Estimated cost of the research phase alone**, assuming a typical ~90% input / 10% output split for read-heavy summarization work (an assumption — Anthropic bills input and output separately, and this repo does not have a token-by-token breakdown), at Claude Sonnet 5 pricing:

| Pricing tier | Input ($2 or $3 / M) | Output ($10 or $15 / M) | Total |
|---|---:|---:|---:|
| Intro pricing (through 2026-08-31) — $2.00 / $10.00 per M | ~1.61M tok → $3.22 | ~0.18M tok → $1.79 | **≈ $5.01** |
| Standard pricing — $3.00 / $15.00 per M | ~1.61M tok → $4.83 | ~0.18M tok → $2.68 | **≈ $7.51** |

This is a lower bound in one sense (prompt caching, which this session used heavily, reduces real billed cost below a naive per-token calculation) and an approximation in another (the 90/10 split is an assumption, not a measurement).

## Estimated cost for the full build (research + design + implementation + docs)

The implementation phase that followed — scaffolding, ~65 backend/frontend/config files, a Docker build, live container verification, architecture/flowchart diagrams, and this documentation set — was **not instrumented with a token counter** in this environment, so the figures below are a **reasoned estimate**, not a measurement. Method: full-stack builds of comparable scope (a FastAPI + React app with 5 AI models, Docker, auth, admin console, and a full documentation set) typically run **2–4×** the token volume of their research phase, because generated code + iterative fixes + long documentation prose all accumulate on top of the same context.

| Phase | Estimated tokens | Estimated cost (intro Sonnet 5 pricing) |
|---|---:|---:|
| Research (measured, see above) | 1.79M | ≈ $5–8 |
| Planning + backend + frontend implementation | 2.5M – 4.5M | ≈ $10–25 |
| Docker build/debug + E2E verification iteration | 0.3M – 0.8M | ≈ $2–6 |
| Documentation (architecture.md, flowchart.md, HTML guide, this prompt set) | 0.8M – 1.5M | ≈ $4–10 |
| **Total (estimated)** | **≈ 5.4M – 8.6M tokens** | **≈ $20 – 50** |

**If you're using a Claude subscription (Pro/Max) instead of pay-per-token API billing**, the relevant framing isn't a dollar cost but a share of your plan's usage — a build this size (a full week-long PoC, done once) is a meaningfully large single session, comparable to several hours of continuous heavy Claude Code use, but is a one-time cost per project, not a recurring one.

## Estimated wall-clock time

| Activity | Estimated time | Why |
|---|---|---|
| Research (measured) | ~4 min | 8 agents in parallel; bounded by the slowest one |
| Planning + user Q&A | ~5–10 min | One clarifying question (frontend stack), one plan review |
| Backend + frontend implementation | ~40–70 min | ~65 files; mostly bounded by generation speed, not thinking time |
| Docker image build (first time) | ~5–15 min | Downloads torch (~155MB CPU wheel) + transformers/diffusers/chromadb/etc.; highly dependent on network speed |
| Model + dataset warm-up (container's first boot) | ~3–8 min | Downloads 4 HuggingFace models (~3.5GB combined) + 2 public datasets (~23MB) once, cached afterward |
| End-to-end verification run | ~5–12 min | Diffusion generation and forecasting are the slowest steps on CPU |
| Documentation + screenshots | ~20–40 min | Mermaid diagrams, bilingual HTML guide, screenshot capture |
| **Total, one AI-assisted session** | **≈ 1.5 – 3 hours** | vs. an estimated **1–2 weeks** for a solo engineer building the equivalent from scratch by hand (research + full-stack build + Docker + docs) |

## Caveats

- **This specific build ran meaningfully longer than the table above** — the table describes a *typical* single pass; this actual session hit unusually slow network conditions during model downloads (documented in `../debug/issue-03-cold-start-timeout-and-readiness-probe.md`, e.g. a single local-LLM warm-up step alone took over 8 minutes at one point), plus went through multiple additional rebuild/re-verify cycles while finding and fixing the 7 real issues in `../debug/`, a full volume-wiped clean-reproducibility test, and a follow-up documentation review pass. No reliable end-to-end wall-clock instrumentation exists for the *whole* session to give a single precise "actual total" figure here — the honest statement is: expect this table's estimates on a normal connection with zero debugging needed; expect several times longer when a build turns up real bugs worth fixing properly, as this one did.
- These are estimates for **one AI coding session producing one PoC**, not a general "AI coding costs X" claim — actual cost scales with how much back-and-forth debugging a given build needs, which varies by task.
- Prompt caching, effort-level tuning, and batching (all covered in this repo's referenced Claude API documentation) can reduce real-world cost well below the naive per-token estimate above.
- Cloud AI usage inside the *running app itself* (the OpenRouter `qwen/qwen3-8b` insight feature) is a separate, much smaller ongoing cost — see `docs/guide.html`'s monthly operating-cost section — and is unrelated to the one-time cost of building the app.
