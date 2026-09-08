# Issue 05 — MAPE reported as 131,574.8% on a real forecast run

## Symptom

A real, manual full-pipeline test (`POST /api/forecast/run` with
`use_openrouter: true`, Korean) returned a nonsensical accuracy figure:

```json
{"mae": 20840.1, "mape": 131574.8}
```

MAE (Mean Absolute Error, ~£20,840 on a series with daily values in the
tens-of-thousands to ~£200k range) is entirely reasonable. MAPE (Mean
Absolute Percentage Error) of **131,574.8%** is obviously wrong — and the
AI-generated insight text dutifully (and correctly, given what it was
told) flagged "매우 낮은" (very low) model accuracy based on that bad number,
which would mislead a real user.

## Investigation

Printed the last 16 days of the `history` array from that same response:

```
2011-11-26  value: 0.0
...
2011-12-03  value: 0.0
```

Both zero-revenue days are **Saturdays**. This UK wholesale retailer simply
doesn't process orders on Saturdays — a real, legitimate weekly pattern in
the data (`data/SOURCES.md`'s UCI Online Retail dataset), not missing or
corrupted data.

## Root cause

`ml/forecast.py`'s backtest MAPE calculation guarded against division-by-zero
by replacing a zero actual value with `1` before dividing
(`np.where(bt_test.values == 0, 1, bt_test.values)`). That prevents a crash,
but not a nonsensical result: on a $0-actual day, any nonzero prediction
error becomes `|error| / 1`, i.e. the raw dollar error is reported *as a
percentage* — a single mispredicted $0 day (predicting even a modest ~£5,000
for what was actually a $0 Saturday) can single-handedly add tens of
thousands of percentage points to the averaged MAPE across a 14-day window.
This is a well-known, textbook weakness of MAPE (undefined/unstable at or
near zero actuals) — not unique to this codebase, but it needed a real,
correct fix rather than a divide-by-zero guard that quietly produces a
misleading number instead of crashing.

## Fix applied

In `ml/forecast.py`:
1. **MAPE now excludes near-zero-actual days** from the average (`actual >
   £1`) instead of substituting a placeholder denominator, and reports how
   many days were excluded via a new `mape_note` field (`None` when nothing
   was excluded).
2. Added **sMAPE** (symmetric MAPE, bounded 0–200% by construction, so it
   can't blow up the same way) as a companion metric that's always defined.
3. The LLM insight prompt (`routers/forecast.py`) now cites sMAPE as the
   primary accuracy figure in its narrative (falling back to also mentioning
   MAPE only when it's actually defined), so the AI-generated insight text
   can't repeat a misleading statistic even if a future backtest window
   again contains a $0-actual day.
4. `models.ForecastRun.mape` is now nullable (was silently defaulting to
   `0.0`, which is just as misleading as the blown-up number — looks like a
   perfect forecast); `smape` was added as a new, always-populated column.

## Verification

Re-ran the same OpenRouter forecast request after the fix — see
`../history/v1.0.0.md` for the corrected metrics and the AI insight text
generated from them.

## What to study if this is new to you

- **MAPE's zero-actual weakness is a standard, well-documented statistics
  pitfall** — introductory time-series material ("시계열 예측 실습") commonly
  introduces MAE/MAPE/MASE together specifically because no single metric is
  safe in every situation; MASE (scaled against a seasonal-naive baseline)
  is a commonly-suggested more-robust alternative for exactly this kind
  of series. sMAPE (used here) is a simpler companion fix for the same
  underlying problem.
- **A silent guard against a crash is not the same as a correct answer.**
  `np.where(x == 0, 1, x)` stops a `ZeroDivisionError`, but the number it
  then produces still needs to be sanity-checked — "doesn't crash" and "is
  meaningful" are different bars, and an LLM summarizing a bad number will
  confidently write a bad (but fluent-sounding) conclusion from it, which is
  exactly what happened here before the fix.
