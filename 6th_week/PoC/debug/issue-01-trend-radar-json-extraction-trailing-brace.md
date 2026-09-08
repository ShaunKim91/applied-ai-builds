# Issue 01 — Trend Radar JSON extraction failed on a real, observed local-model output

**Found**: during Playwright screenshot capture — asking Trend Radar to evaluate "Cursor IDE" a second
time (the first, in `verify_e2e.py`, happened to succeed) returned `extraction_failed: true`, with the
raw model output visibly looking like valid JSON.

## Root cause

`Qwen2.5-0.5B-Instruct`'s real output for this request was:

```
{"cost": {"level": "Insufficient evidence", "note": "No specific cost details provided."}, "security": {"level": "Insufficient evidence", "note": "No security measures mentioned."}, "approval": {"level": "Insufficient evidence", "note": "Sources lack detailed approval processes."}}}
```

— a syntactically-complete, correctly-shaped JSON object, followed by **one stray extra `}`**. The
original `parse_radar_json()` extracted a JSON candidate with `_JSON_BLOCK_RE = re.compile(r"\{.*\}",
re.DOTALL)` — a greedy regex that matches from the first `{` to the **last** `}` in the text. On this
input, that swallowed the stray extra brace into the "candidate" string, so `json.loads()` failed on
what was otherwise perfectly valid JSON, and the feature correctly (but unnecessarily) fell back to its
honest "extraction failed" path.

## Fix

Replaced the greedy regex with `_extract_first_json_object()`, a small brace-depth counter (with
string/escape awareness, so a `}` character inside a quoted note doesn't miscount) that finds the
substring from the first `{` to **its own matching** `}` and ignores anything after. This recovers the
real, correct verdict even when the model appends trailing garbage, while still returning `None` (never
fabricating a result) for genuinely non-JSON output.

## Verification

- Re-ran the exact captured malformed string through the fixed extractor (standalone, stdlib-only
  script, then again after rebuilding the image) — now parses correctly, all three lenses recovered.
- Re-verified a prose-wrapped clean-JSON case and a fully-non-JSON case both still behave correctly
  (extract vs. correctly return `None`).
- Rebuilt the image, re-ran `verify_e2e.py`, and re-ran the Trend Radar screenshot capture — see
  `history/v1.0.0.md`.
