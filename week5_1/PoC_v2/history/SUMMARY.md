# Verity — Summary

**Week5_1 PoC_v2. Topic: search APIs, embedding-based reranking, search+LLM grounding. Product: a
grounded claims-research assistant for a named fictional company and a named persona — a complete,
commercial-grade rebuild replacing the earlier "Compass" PoC, not an incremental update to it.**

## What it is

Verity researches Fenwick Mutual's (a fictional regional P&C insurer) claims questions strictly
against a fully fictional, code-defined jurisdiction corpus — never live web search, deliberately,
to avoid any risk of echoing real regulatory text as if verified. It produces either a free-form
Quick Answer or a structured Precedent Brief (Issue / Governing Authority / Facts Applied /
Recommendation / Sources), checks its own work three independent ways (citation-marker validity +
content-similarity groundedness, URL-level ghost-citation detection, and a new entity-hallucination
cross-check this build's own testing found necessary), highlights possible fraud-pattern signals,
tracks catastrophe events as first-class objects, and evaluates real AI/InsurTech vendor tools
against a real live-web-grounded Cost/Security/Approval-friction framework.

## Why this is a rebuild, not an update

The prior "Compass" PoC was functionally solid but never stated who it was for — a gap shared by
every other product in this series (CommerceIQ, VoxIQ, Parchment, Lucent all used only a generic
functional category name). This round's explicit feedback asked for a named target, a completely
different approach from Weeks 1-4, and commercial-grade (not PoC-grade) quality. Verity answers
all three: a specific persona (Dana Whitfield) and company (Fenwick Mutual) stated on a public
landing page before login, a sixth distinct design identity shared deliberately with its Week5_2
companion Threshold as one product suite, and a real security/observability bar (rotating auth
tokens, CSRF, account lockout, a hash-chained tamper-evident audit log, rate limiting, real
p50/p95/p99 metrics) that no prior product in this series — including Compass — implemented.

## What's genuinely new this round

- A named target persona and company, stated explicitly, addressing this round's core feedback
- An `Organization` data model (structurally multi-tenant-ready) instead of a hardcoded singleton
- Access+refresh token rotation, CSRF double-submit, account lockout — replacing every prior PoC's
  flat 24h JWT
- A hash-chained, tamper-evident audit log with a live integrity-verification admin action
- Real per-route p50/p95/p99 latency tracking and a structured error log
- A deliberate split between fictional-corpus-only claims research and real-live-web vendor
  evaluation, with the reasoning documented explicitly
- An entity-hallucination cross-check, added specifically because this build's own testing found a
  real gap in sentence-similarity-based groundedness scoring

## The three real bugs found and fixed (not fabricated)

A measured embedding-similarity false-positive that flagged every fraud pattern on unrelated
questions (fixed: keyword-only matching); a measured gap where a hallucinated real-world federal
agency name scored a perfect groundedness score (partially mitigated: a deterministic entity
cross-check, honestly disclosed as incomplete); and a latent race condition in entry-loading logic
(fixed structurally). Full write-ups: `../debug/`. Two non-product Playwright wait-condition traps
were also found and fixed in the screenshot tooling itself.

## Verification performed

- 25-check `verify_e2e.py`, all passing on the final clean rebuild — the largest check count of any
  product in this series, reflecting the added commercial-grade surface area
- Real OpenRouter escalation call, real live-web Vendor Radar call, both with real measured latency
  pulled from the hash-chained audit log
- A direct tamper-detection regression proving the audit-log hash chain actually catches corruption,
  not just that it reports "intact" trivially
- A full clean-rebuild reproducibility test (`docker compose down -v` + rebuild), consistent bootstrap
  timing with the historical Compass baseline for the same 3-model set
- Playwright screenshots of all 8 primary screens plus a dark-mode variant
- Double-independent-method API-key-leakage scan — clean

## Status

Complete and self-verified. Awaiting user review before proceeding to Threshold (Week5_2's
companion rebuild).
