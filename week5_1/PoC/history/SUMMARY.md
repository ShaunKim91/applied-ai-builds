# Compass — Summary

**Week5_1 PoC. Topic: search APIs & trend research. Product: a streaming, web-search-grounded
research assistant, built to keep escalating UI/UX and overall product quality one more notch past
Weeks 10-13.**

## What it is

Compass is a research assistant that searches the live web (via `ddgs`, free, no key), reranks
results with a bi-/cross-encoder pair, and streams a cited report from a real LLM — checking its own
work two independent ways (citation/content groundedness, reused from Week4, plus a new
URL-level "ghost citation" check, generalizing a common introductory citation-verification technique
that a typical baseline implementation of this pattern never implements). It archives every report
for later semantic search, compares its own free pipeline against OpenRouter's fully-managed
web-search product side by side, evaluates AI tools/trends against a real 3-lens framework, and
enforces an admin-configurable daily spend cap on any paid call — a standard cost-governance
discipline that a typical baseline implementation's code never implements either.

## Why it's a real step up from a typical baseline implementation

A typical baseline implementation of this pattern's default path calls **no LLM at all** — a
rule-based template lists reranked snippets, byte-for-byte identical whether run once or a hundred
times, with no persistence, no auth, and no cost control anywhere in its code. Compass implements
the thing that baseline only gestures at: real generation, real persisted history, a real searchable
archive, and the two disciplines (grounding verification, cost governance) that are widely
recognized as important but that baseline skips. Full dimension-by-dimension comparison in
`architecture.md` §2.

## What's genuinely new this round (not reused from Weeks 10-13)

- A live, unreliable external retrieval dependency (`ddgs`) handled with a real, per-request
  mock-fallback design — not just at bootstrap, but on every single query
- A URL-level ghost-citation checker, a distinct verification axis from Week4's sentence-similarity
  groundedness check
- Two independent uses of the OpenRouter API in one product — an ordinary chat-completion call and
  its separate, fully-managed web-search plugin — compared head-to-head in a dedicated Grounding Lab
- A real, enforced cost-governance budget cap — the first governance feature (as opposed to
  analytics) in any Admin console across this whole project series
- A fourth distinct design language, and the first app in this series to default to dark rather than
  light, with a genuine three-way typographic system and a real motion layer (radar-sweep,
  skeleton shimmer)

## The one real bug found and fixed (not fabricated)

Trend Radar's structured JSON extraction failed on a real, valid `Qwen2.5-0.5B-Instruct` output that
happened to include one stray trailing `}` — a greedy regex swallowed the extra brace into its parse
candidate. Fixed with a brace-depth-counting extractor; re-verified against the exact captured
malformed output. Full write-up: `../debug/`. Two separate, non-product ambiguities in the
screenshot-testing tooling itself (Playwright selector precision) were also found and fixed, and are
disclosed transparently as test-tooling issues rather than conflated with product bugs.

## Verification performed

- 16-check `verify_e2e.py`, run 3 times across this build (14 checks on the first two runs, 16 after
  adding two regression tests), all passing every time
- OpenRouter real-key tests on both call shapes: the managed web-search plugin (4 real calls) and
  plain chat-completion synthesis (1 real call)
- A full clean-rebuild reproducibility test (`docker compose down -v` + rebuild)
- Playwright screenshots of all 6 primary screens plus a light-mode variant
- Double-independent-method API-key-leakage scan (wrapped `grep` + ground-truth `command grep`) —
  clean

## Status

Complete and self-verified. Awaiting user review before proceeding to Week5_2.
