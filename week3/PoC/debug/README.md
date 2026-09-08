# Debug Log — Parchment (Week3 PoC)

This folder records real issues hit while building and verifying this
project — root cause, fix, and (where relevant) the underlying concept
involved — so it doubles as a troubleshooting reference for anyone
extending this PoC or repeating a similar build.

Each issue gets its own `issue-NN-short-slug.md` file. This README is the
index; it is updated as issues are found, not written speculatively.

| # | Title | Root cause category |
|---|---|---|
| [01](issue-01-pdf-summarize-timeout-on-real-document.md) | PDF summarization timed out (180s) on the real Fed report, and read poorly even after a partial fix | Naive per-chunk sequential summarization doesn't scale to a genuinely long real-world document (34,000 words → 191 chunks) — **real bug, fixed** (batched inference + larger chunks + an explicit, surfaced cap; verified 56.7s and materially better summary quality) |
| [02](issue-02-numeric-check-percent-notation-mismatch.md) | Numeric cross-check false-flagged a real, source-backed number ("2%" vs. source's "2 percent") | Exact-substring matching doesn't recognize equivalent notations — **real bug, fixed** (percent-form normalization added; re-verified against the same real document) |

## How these were found

Both found by actually exercising the running app against the real bundled
Fed report — issue 01 by the first real `verify_e2e.sh` run (deliberately
using a genuinely long document, not a toy one, so a scaling problem would
surface during verification rather than in front of a real user); issue 02
by directly testing the OpenRouter cloud path with a real key against the
same document, which happened to phrase a true fact differently than the
local summarizer had.
