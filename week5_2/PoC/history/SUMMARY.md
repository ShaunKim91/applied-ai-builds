# Cradle — Summary

**Week5_2 PoC. Topic: agentic AI fundamentals (ReAct loop, local-LLM agents, safety guardrails).
Product: a local ReAct agent console with real, wired safety guardrails, built with a first-time
explicit request for genuine 3D/spatial-depth UI and a pastel claymorphism visual language.**

## What it is

Cradle runs a local `Qwen2.5-0.5B-Instruct` model as a real ReAct (Thought→Action→Observation)
agent that calls real tools (calculator, date lookup, currency conversion, FAQ lookup, refund
issuance), rendering its own reasoning as a layered 3D card stack. Every tool call passes through
four guardrails in a deliberately corrected order (step limit → permission → cost cap → HITL) — a
naive implementation of this pattern is easy to get wrong here. The one guardrail a typical
baseline implementation builds but never wires into its app, Human-in-the-Loop approval, is made
real here: a gated tool call actually pauses execution, and an admin's real approve/deny decision
actually resumes it, potentially long after the original request ended. An opt-in, budget-gated
escalation to OpenRouter's `qwen/qwen3-8b` implements a well-documented "model routing" trend for
when the local agent stalls.

## Why it's a real step up from a typical baseline implementation

A typical baseline implementation of this pattern is a 2-tab Streamlit app where the ReAct agent tab
and a guardrail-demonstration tab never actually talk to each other — the agent you chat with isn't
the one the guardrails wrap. Its `approval_required_tools` class feature stays an empty set in the
shipped app, so HITL never triggers in the real demo, and its guardrail check order is easy to get
wrong (cost cap checked before permission), which mislabels unauthorized-tool attempts in exactly
the kind of audit trail meant to catch them. Cradle implements the thing that kind of baseline only
gestures at: one integrated agent, guardrails always in the path, HITL that actually pauses and
resumes real execution, and the corrected check order — full comparison in `architecture.md` §2.

## What's genuinely new this round (not reused from Weeks 10-14_1)

- A resumable, DB-persisted agent loop — one shared generator function consumed two ways (live SSE
  for a fresh run, synchronous drain to resume a paused one), the first PoC in this series where a
  single "request" can genuinely pause and continue across an unrelated later HTTP call
- A real, actionable Human-in-the-Loop approval queue with a genuine pause/resume execution path
- An explicit, documented correction of a common guardrail-ordering pitfall identified during design
- Model routing as a real, opt-in, budget-gated feature (not a redundant second web-search vendor)
- A fifth distinct design language, and the first in this series with genuine spatial-depth
  interaction: a pointer-reactive 3D tilt component, a two-directional claymorphism shadow system,
  and a layered card-stack visualization of the agent's own reasoning steps

## The six real bugs found and fixed (not fabricated)

Two were caught during design research and corrected proactively before ever being shipped (the
guardrail-order pitfall); four were found via manual browser testing and direct audit-log inspection
during this build's own verification — a stale streaming box + duplicated answer on reload, runs
permanently stuck `RUNNING` after a client disconnect, a live-vs-reopened step-numbering mismatch,
an E2E test that polluted the real admin account with synthetic data, and an audit-log `latency_ms`
column hardcoded to `0.0` everywhere it was ever logged. Full write-ups: `../debug/`. Three separate,
non-product ambiguities in the screenshot-testing tooling itself were also found and fixed, disclosed
transparently rather than conflated with product bugs.

## Verification performed

- 16-check `verify_e2e.py`, run 4 times across this build (one run hit a real, transient external
  OpenRouter rate limit — reported honestly, not hidden — and passed clean on retry), 16/16 on the
  final run
- OpenRouter real-key escalation test, with a real measured latency (22.7s) pulled directly from the
  audit log after fixing the bug that made that column always read 0
- Three full clean-rebuild reproducibility tests (`docker compose down -v` + rebuild), each
  triggered by a real code fix, with consistent ~11m20s bootstrap timing across all three
- Playwright screenshots of all 6 primary screens plus an awaiting-approval state and a dark-mode
  variant (8 total)
- Double-independent-method API-key-leakage scan (wrapped `grep` + ground-truth `command grep`),
  re-run against the final tree after this session's last code changes — clean

## Status

Complete and self-verified. Awaiting user review before proceeding to Week6_1.
