# AI Engineering Projects — Weekly Products

A portfolio of full-stack AI products, one per week of an applied AI/ML project series — computer
vision, LLM internals & document AI, RAG, and agentic AI. Each is a real, working, Dockerized
full-stack app (FastAPI + React/TypeScript), not a notebook demo — with auth, a database, an admin
console, and bilingual (EN/KO) documentation.

> Every product runs local-first (HuggingFace models, CPU-only) with an optional, budget-capped cloud
> escalation via OpenRouter — nothing here requires a paid API key to run.
> Companion repo of rewritten lesson notes covering the same weekly topics:
> [`ai-curriculum`](https://github.com/ShaunKim91/ai-curriculum).

## 🧵 Featured: the "Fenwick Mutual" suite (Week 6–8)

Three connected products for one fictional regional insurer, sharing one design system and one
commercial-grade security/observability architecture (JWT access+refresh rotation, CSRF, account
lockout, a hash-chained tamper-evident audit log, real p50/p95/p99 metrics) — each built for a
specific, named persona rather than a generic feature list.

| Product | For | What it does |
|---|---|---|
| **[Verity](week6/PoC_v2/projects/verity/)** | Dana Whitfield, Senior Claims Research Analyst | A grounded research assistant — cited precedent briefs, hallucinated-citation checking, fraud-signal detection over a fictional (never real) regulatory corpus |
| **[Threshold](week7/PoC_v2/projects/threshold/)** | Priya Nakamura, Claims Processing Team Lead | A guardrailed ReAct agent console — amount-aware Human-in-the-Loop approval so no payout above a threshold can bypass review |
| **[Throughline](week8/PoC/projects/throughline/)** | Marcus Webb, Policyholder Services Rep | A LangChain conversational-memory copilot — persisted dual-strategy memory, structured fact extraction, a memory-write conflict guardrail |

Each has its own bilingual operations guide (`docs/guide.html`), architecture doc with Mermaid
diagrams, an honest debug log of real bugs found via manual testing, and a real-numbers build log
(`history/v1.0.0.md`) — Docker image size, boot time, and end-to-end test results, all actually
measured.

## All products

| Week | Topic | Product(s) |
|---|---|---|
| 1 | Computer vision & generative image models | [CommerceIQ](week1/PoC/projects/commerceiq/) — commerce ops: catalog vision, a generative studio, demand forecasting, semantic search |
| 2 | LLM internals, embeddings, audio AI | [VoxIQ](week2/PoC/projects/voxiq/) — meeting & knowledge intelligence: transcription, retrieval reranking, an analytics agent |
| 3 | Multimodal document AI | [Parchment](week3/PoC/projects/parchment/) — document intelligence: receipt OCR+VLM, PDF summarization, table scraping |
| 4 | RAG | [Lucent](week4/PoC/projects/lucent/) — streaming RAG chat with inline citations and an automated groundedness check |
| 6 | Search-grounded research | [Compass](week6/PoC/projects/compass/) → **[Verity](week6/PoC_v2/projects/verity/)** (see suite above) |
| 7 | Agentic AI fundamentals | [Cradle](week7/PoC/projects/cradle/) → **[Threshold](week7/PoC_v2/projects/threshold/)** (see suite above) |
| 8 | LangChain agents & memory | **[Throughline](week8/PoC/projects/throughline/)** (see suite above) |

`PoC/` = the original weekly build. `PoC_v2/` = a from-scratch, commercial-grade rebuild of that same
product, done after direct feedback that every prior product needed a clearer stated target — both
are kept side by side so the before/after is visible, not overwritten.

## Running any project

```bash
cd week<N>/PoC[_v2]/projects/<name>/
./scripts/setup.sh          # builds the image, starts the container, waits for health
./scripts/verify_e2e.sh     # full end-to-end verification suite
```

Requirements: Docker Desktop, ~5GB free disk per project, internet for the one-time model download.
Demo admin credentials are printed by `setup.sh` and documented in each project's own README.

## A note on API keys

No real API key is included anywhere in this repo. To try the optional cloud-escalation feature in
any project, create your own `api_keys/openrouter.md` (one level above wherever you clone each
project into, matching that project's own `docker-compose.yml` volume mount, adjusted to your own
layout) — every project works fully without one, falling back to local-only inference.

## License

Original portfolio work. All companies, personas, and data referenced (e.g. "Fenwick Mutual") are
fictional. Third-party libraries and models retain their own licenses, documented in each product's
own `docs/guide.html`.
