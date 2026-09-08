# Lucent — Summary

**Week4 PoC. Topic: document search & VectorDB/RAG. Product: a streaming, citation-grounded RAG
chat assistant, built explicitly to be more advanced, more transparent in UI, and higher product
value than Weeks 10-12.**

## What it is

Lucent is a multi-turn chat assistant that answers questions strictly from a real, bilingual
knowledge base (the 85 Federalist Papers essays in English + a topically-matching Korean Wikipedia
article), streaming its answer token-by-token, citing every claim with a `[n]` marker traceable to
an actual retrieved passage, and automatically checking its own answer's groundedness before
showing it to the user.

## Why it's a real step up from a typical baseline implementation

A typical baseline implementation of this pattern has **no LLM call in its default path at all**
— it returns the top-ranked chunk through a rule-based template. Lucent implements the thing that
baseline only gestures at: real generation, real multi-turn memory, a real persistent vector
store, real overlapping chunking, and a real automated check that the generated answer didn't
drift from its sources. Full dimension-by-dimension comparison in `architecture.md` §2.

## What's genuinely new this round (not reused from Weeks 10-12)

- Real token-by-token streaming, both local (`TextIteratorStreamer` on a background thread) and
  cloud (hand-parsed OpenAI-compatible SSE over `httpx.stream`)
- A groundedness verifier generalizing Week3's numeric cross-check into full-answer citation +
  content validation
- A from-scratch glassmorphism design system (gradient-mesh background, translucent panels, a
  floating glass sidebar) — a third distinct visual language after Weeks 10/11 and 12
- A genuine cross-lingual retrieval demonstration, backed by a real Korean-language corpus on the
  same topic as the English one, not just an assertion that the embedding model is multilingual

## Real bugs found and fixed (not fabricated)

1. Korean Wikipedia's API rejected requests with no `User-Agent`, and that single failure was
   silently taking the *entire* English corpus's indexing down with it.
2. The groundedness badge worked live but vanished the moment a chat session was reopened, due to a
   shape mismatch between the streaming and REST-reload code paths.
3. Two real, distinct historical variants of Federalist No. 70 (a genuine feature of the Gutenberg
   source text) shared one identical, ambiguous document title.

Full write-ups: `../debug/`. Full timing, counts, and re-verification: `v1.0.0.md`.

## Verification performed

- 13-check `verify_e2e.py`, run 4 times across this build, 13/13 every time
- OpenRouter real-key streaming test, run twice, including one case where the system correctly
  declined to answer rather than hallucinate
- A full clean-rebuild reproducibility test (`docker compose down -v` + rebuild), twice
- Playwright screenshots of all 7 primary screens, including a dark-mode variant
- Double-independent-method API-key-leakage scan (wrapped `grep` + ground-truth `command grep`) —
  clean

## Status

Complete and self-verified. Awaiting user review before proceeding to Week5_1.
