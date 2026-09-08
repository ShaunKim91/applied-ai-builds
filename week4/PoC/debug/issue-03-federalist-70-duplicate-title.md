# Issue 03 — Two Federalist No. 70 documents share one identical, ambiguous title

**Found**: while writing up final document counts for `history/v1.0.0.md`. `GET /api/documents`
reported 86 English seed documents, not the expected 85 — and `Counter` over their titles showed
`{'Federalist No. LXX': 2}`.

## Root cause — genuinely NOT a parsing bug, but a real title-collision bug

This is the same "86 vs. 85" anomaly flagged during planning (see `plan/v1_plan.md`) — at the time it
was assumed to be a stray/degenerate regex match and left unexplained, defensively guarded only by
`_MIN_ESSAY_CHARS`. Investigating it properly this time (`docker exec lucent python3 -c "..."` against
the actual cached `federalist_papers.txt`) found the real explanation: it is **not** a parsing bug at
all. Project Gutenberg's own transcription of eBook #18 contains an explicit editorial note —

> *(There are two slightly different versions of No. 70 included here.)*

— and then prints both textual variants of Federalist No. 70 back-to-back, each under an identical
`No. LXX.` heading. `_ESSAY_HEADING_RE` correctly finds both; `_MIN_ESSAY_CHARS` correctly does not
filter either one out, because both are real, full-length essay text, not degenerate cross-references.
So 86 is the **correct** count of real headings in this source text.

The actual bug: `parse_federalist_essays()` labeled both variants identically as `"Federalist No.
LXX"`, so once indexed as two separate `Document` rows, a `[n]` citation naming "Federalist No. LXX"
in a chat answer or the Documents page was ambiguous — a user (or the LLM itself) had no way to tell
the two textual variants apart.

## Fix

`parse_federalist_essays()` now counts label occurrences and appends `" (variant 1 of 2)"` /
`" (variant 2 of 2)"` (in source order) whenever a numeral repeats, leaving all 84 non-duplicated
essays' labels unchanged. General-purpose — not hardcoded to "LXX" — so it transparently handles this
one real case in the current source text without assuming it's the only possible one.

## Verification

- Ran `parse_federalist_essays()` against the real cached source text directly inside the container and
  confirmed: 86 labeled essays, 85 unique base numerals, the two Federalist No. 70 entries now labeled
  `"Federalist No. LXX (variant 1 of 2)"` and `"Federalist No. LXX (variant 2 of 2)"`.
- Wiped the seed corpus's indexed `Document` rows and Chroma vectors, re-ran the bootstrap indexing
  step, and confirmed via `GET /api/documents` that both variants now appear with distinct titles and
  no other essay's title changed.
- Re-ran `verify_e2e.py` (13/13) and the OpenRouter real-key streaming test again after this fix — see
  `history/v1.0.0.md`.
