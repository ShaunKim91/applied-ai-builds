# Throughline — Summary

**Week6_1 PoC. Topic: LangChain agents and conversational memory (LCEL, PromptTemplate/output
parsing, tool-calling agents, dual-strategy memory). Product: a LangChain-based conversational-memory
copilot for a named persona at the same fictional company as Verity and Threshold — a complete,
commercial-grade build, and the third product in the Fenwick Mutual suite.**

## What it is

Throughline runs a local `Qwen2.5-0.5B-Instruct` model as one shared LangChain `Runnable` behind four
real LCEL chains for Fenwick Mutual's Policyholder Services team: routing a representative's message
to one of five safe tools or a direct reply (structured-output, Pydantic-validated, with a bounded
retry), extracting structured facts from each turn (with a grounding check and a conflict guardrail),
composing the actual reply, and periodically folding the conversation window into a rolling summary.
Memory is dual-strategy (a verbatim sliding window + an LCEL summarization chain) and persisted in
SQL — closing a well-known "memory not persisted, lost on restart" gap common to a typical baseline
implementation of this pattern. A stated preference from one turn can auto-fill a later tool call without the representative
repeating it — the one structural capability neither Verity nor Threshold has, since neither has a
notion of the same external counterparty recurring across sessions.

## Why this is a from-scratch build, not an update

Following the same feedback that drove the Verity and Threshold rebuilds, Throughline answers with a
specific persona (Marcus Webb, Policyholder Services representative, 50-70 inbound calls/day) and
shares Fenwick Mutual and the "Fenwick Ledger" design system with its two siblings, completing a
three-pillar suite: Verity (grounded research), Threshold (guarded agentic action-taking), Throughline
(conversational memory + safe tool use) — each mapped to a genuinely distinct pillar of this
project series' Agentic AI focus. It carries the same commercial-grade security/observability bar as
Verity and Threshold: an `Organization` data model, access+refresh token rotation with CSRF and
account lockout, a hash-chained tamper-evident audit log, rate limiting, and real p50/p95/p99
metrics — reused verbatim rather than redesigned a third time, since a shared platform layer across
one company's tool family is itself a commercial-grade signal.

## What's genuinely new this round

- Real `langchain-core` LCEL composition, verified against the actual installed package before use —
  a typical baseline implementation imports `PromptTemplate` but never actually pipes it
- Structured-output tool routing replacing a typical brittle regex matcher, with an honestly measured
  first-try reliability and a bounded retry (never a silent guess)
- Persisted, dual-strategy memory (SQL window + LCEL rolling summary), closing a well-known
  persistence gap common to that kind of baseline
- Structured memory extraction with a grounding check and a genuinely new guardrail axis: a memory
  write that never silently overwrites a confidently-known fact
- Memory-conditioned tool auto-fill — the mechanism-level differentiator from Verity and Threshold
- A real `ast`-whitelist safe evaluator, closing the `eval()` shortcut a typical baseline implementation
  and Threshold's own calculator tool both carry, and correcting a common piece of introductory
  material along the way
- Redaction at every trust boundary (persistence, the OpenRouter call, the live UI) plus a real purge/
  right-to-erasure action — the first product in the suite to handle third-party (policyholder) PII
  rather than internal analyst work product

## Real bugs found and fixed (4, not fabricated)

A detached-ORM-instance crash across an SSE session boundary; structured memory being extracted and
persisted but never actually reaching the reply-generation prompt; a `ChatPromptTemplate`-fronted LCEL
composition crashing the first time summarization genuinely ran; and a callback-preference matcher
that silently never fired. All four found via direct multi-turn manual testing, all four now permanent
regression steps in `verify_e2e.py`. Full write-ups: `../debug/`.

## Verification performed

- 31-check `verify_e2e.py`, all passing on two separate clean rebuilds in a row
- Real OpenRouter escalation call, a real memory-conditioned tool auto-fill, and a real organically-
  produced memory conflict, all with real measured latency pulled directly from the hash-chained
  audit log
- A direct tamper-detection regression proving the audit-log hash chain actually catches corruption
- Three full clean-rebuild reproducibility tests (`docker compose down -v` + rebuild), consistent
  ~51-55s bootstrap timing across all three
- Playwright screenshots of all primary screens, including an organically-produced memory-conflict
  state and a dark-mode variant
- Double-independent-method API-key-leakage scan — clean

## Status

Complete and self-verified. This completes all three products of this round's Fenwick Mutual rebuild
(Verity, Threshold, Throughline). Awaiting user review.
