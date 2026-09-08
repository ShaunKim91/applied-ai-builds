# Threshold — Summary

**Week5_2 PoC_v2. Topic: agentic AI fundamentals (ReAct loop, local-LLM agents, safety guardrails).
Product: a guardrailed ReAct agent console for a named persona at the same fictional company as
Verity (Week5_1's companion rebuild) — a complete, commercial-grade rebuild replacing the earlier
"Cradle" PoC.**

## What it is

Threshold runs a local `Qwen2.5-0.5B-Instruct` model as a real ReAct agent for Fenwick Mutual's
claims processing team, calling seven real tools (filing-deadline lookup, policy coverage lookup,
payout arithmetic, currency conversion, procedure lookup, payout issuance, and a never-allowlisted
decoy). Every tool call passes through four guardrails in the corrected order (step limit →
permission → cost cap → HITL — a common bug in naive implementations of this pattern gets this order
wrong). Payout issuance is gated by an **amount-aware** Human-in-the-Loop check — a real engineering
upgrade over the predecessor Cradle PoC's flat per-tool-name gate — so a small payout auto-approves
while a large one genuinely pauses for a human decision. An opt-in, budget-gated escalation to
OpenRouter's `qwen/qwen3-8b` implements a common "model routing" pattern for combining local and
cloud models, with a hard security invariant: the escalation path has zero tool-calling capability.

## Why this is a rebuild, not an update

Following the same feedback that drove Verity's rebuild — no prior PoC in this project series stated a
target persona — Threshold answers with a specific persona (Priya Nakamura, Claims Processing Team
Lead) and shares Fenwick Mutual and the "Fenwick Ledger" design system with Verity, forming one
connected product suite rather than two independently-styled weekly builds. It carries the same
commercial-grade security/observability bar as Verity: an `Organization` data model, access+refresh
token rotation with CSRF and account lockout, a hash-chained tamper-evident audit log, rate
limiting, and real p50/p95/p99 metrics — none of which the predecessor Cradle PoC implemented.

## What's genuinely new this round

- Amount-aware HITL — the single biggest behavioral upgrade over Cradle's flat per-tool-name gate
- The corrected guardrail check order made *visible* in the Admin UI, not just implemented silently
- A genuinely new tool (`lookup_policy_coverage`) reflecting a real distinct examiner task
- The full commercial-grade security/observability suite, shared architecture with Verity
- A real, two-part bug in tool-argument parsing, found and fixed with a general solution (not a
  narrow patch) that handles both quoting conventions a small local model naturally produces

## The one real bug found and fixed (two manifestations, not fabricated)

A quoted string argument (`lookup_claims_procedure("subrogation")`) broke keyword matching for a
real, existing procedure; a second manifestation surfaced while verifying the first fix — two
separately-quoted, comma-separated arguments broke a different tool the same way. Both are fixed by
one general, correctly-designed helper (`tools.py`'s `clean_arg()`/`split_args()`), not two separate
patches. Full write-up: `../debug/`. Unlike Cradle (which shipped six real bugs), Threshold carried
forward every one of Cradle's own hard-won lessons correctly from the start.

## Verification performed

- 26-check `verify_e2e.py`, all passing on the final clean rebuild
- Real OpenRouter escalation call and real HITL approve/deny flows, both with real measured latency
  pulled directly from the hash-chained audit log
- A direct tamper-detection regression proving the audit-log hash chain actually catches corruption
- Three full clean-rebuild reproducibility tests (`docker compose down -v` + rebuild), consistent
  ~11m30s bootstrap timing across all three
- Playwright screenshots of all primary screens plus a dark-mode variant
- Double-independent-method API-key-leakage scan — clean

## Status

Complete and self-verified. This completes both halves of this round's rebuild (Verity + Threshold)
as one connected Fenwick Mutual product suite. Awaiting user review before proceeding to Week6_1.
