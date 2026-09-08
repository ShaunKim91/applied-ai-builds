# Issue 02 — The fraud-signal embedding fallback flagged every pattern on every query

**Found**: while visually inspecting a real research-query screenshot, a completely mundane
prompt-payment-deadline question came back tagged with **all five** fraud-pattern signals at once
("Possible staged-collision indicator", "Possible inflated-contractor-invoice pattern", "Possible
phantom-vehicle claim", "Possible post-binding-loss timing pattern", "Possible duplicate-claim-ring
pattern") — a result that should be structurally impossible for an unrelated query and immediately
suspicious.

## Root cause

`fraud_signals.check()` matched by keyword first, then fell back to embedding cosine similarity
(`intfloat/multilingual-e5-small`, threshold 0.62) against each pattern's description for anything
that didn't hit a keyword. Measured directly (not assumed) inside the running container:

```
"How quickly must Fenwick Mutual pay the undisputed portion of a claim in Cedermoor?"
  staged-collision: 0.816   inflated-contractor-invoice: 0.823   phantom-vehicle: 0.799
  post-binding-loss: 0.821  duplicate-claim-ring: 0.816

"The weather in Cedermoor was mild this week." (a wholly generic, unrelated sentence)
  staged-collision: 0.762   inflated-contractor-invoice: 0.781   phantom-vehicle: 0.742
  post-binding-loss: 0.755  duplicate-claim-ring: 0.756

Two genuinely relevant paraphrases (no exact keywords), for comparison:
  "...same person as the only person who saw it happen" -> staged-collision: 0.855
  "...no camera footage, no police report, and nobody else saw it" -> phantom-vehicle: 0.887
```

Every score sits in the 0.74–0.89 range regardless of actual relevance — there is no threshold that
separates the genuine paraphrased positives (0.765–0.887) from the false positives on completely
unrelated or even generic text (0.742–0.823); the ranges overlap entirely. This embedding model's
cosine similarity tracks topical/domain adjacency ("this is insurance-claims-shaped text"), not the
specific factual match a fraud signal needs — a well-documented characteristic of some sentence
embedding models on short, domain-narrow text, now confirmed directly for this exact
model+domain+threshold combination rather than assumed safe.

## Fix

Removed the embedding-similarity fallback entirely. `fraud_signals.check()` is now keyword-only —
strictly less recall (won't catch a paraphrase with no matching keyword) in exchange for materially
higher precision (never fires on unrelated text). For a compliance-facing "signal, not noise"
feature, a check that occasionally under-fires is far more useful than one that fires on nearly
everything: the latter trains its own users to ignore it, which is a worse real-world outcome than
occasionally missing a paraphrased case.

## Verification

- Reproduced the false-positive directly via the measurements above, run inside the container
  against the real embedding model.
- After the fix: the same unrelated prompt-payment question returns zero fraud signals; the keyword-
  based staged-collision case (already covered by an existing E2E check) still fires correctly.
- Added `verify_e2e.py::step_fraud_signal_regression`'s second assertion — an unrelated question must
  return `[]` — so this specific false-positive class has a permanent regression test, not just a
  one-time manual check.
