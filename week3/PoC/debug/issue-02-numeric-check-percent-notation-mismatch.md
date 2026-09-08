# Issue 02 — Numeric cross-check false-flagged a real, verifiable number

## Symptom

Testing the OpenRouter (`qwen/qwen3-8b`) summarization path directly against
the real Fed report sample produced:

```json
{
  "summary_text": "... The Fed aims to maintain a 2% inflation target ...",
  "numeric_check_passed": false,
  "numeric_check_detail": "2%"
}
```

The Fed's 2% inflation target is real, well-documented, and — as it turns
out — genuinely stated in the source PDF. The numeric cross-check
(`ml/summarizer.py::numeric_cross_check`) was flagging it as "unverified"
anyway.

## Root cause

`numeric_cross_check` did an exact substring match between each number the
summary stated and the raw source text. Checking directly:

```python
'2%' in text          # False
'2 percent' in text   # True
```

The source PDF spells the figure out as **"2 percent"**; the LLM's summary
used the **"2%"** symbol form — a paraphrase of the exact same fact, not a
fabrication. The naive string check had no way to recognize the two as
equivalent, so a real, source-backed number was reported as unverifiable —
a false positive in the opposite direction from what this check exists to
catch (it's supposed to catch invented numbers, not correctly-cited ones
written in a different notation).

## Fix applied

Added `_appears_in()` in `ml/summarizer.py`: for any summary number ending
in `%`, it also checks the source text for that number followed by
"percent"/"per cent" (case-insensitive, tolerant of whitespace) before
declaring it unverified. Plain (non-percent) numbers are unaffected —
still checked via the original exact-substring rule.

## Verification

Re-ran the identical OpenRouter request against the same source document:
`numeric_check_passed` is now `true` with an empty `numeric_check_detail`,
for a summary that again states "a 2% inflation target." Re-ran the full
`verify_e2e.sh` suite afterward — 13/13 still pass.

## What to study if this is new to you

- **A verification check can itself be wrong in either direction.** This
  project's "numbers must trace to the source" discipline is only useful if
  it doesn't also reject *correct* citations — a check that cries wolf on
  real facts trains users to ignore it, which is arguably worse than not
  having the check at all.
- **This was found by directly exercising the cloud path with a real key**,
  not by reading code — `debug/issue-01`'s fix was validated on the local
  summarizer, but the OpenRouter path uses a different (larger, more
  fluent) model that happened to choose a different, equally correct way of
  writing the same number. Testing both code paths against the same real
  document surfaced a bug neither path alone would have shown clearly.
