# Issue 02 — Local 0.5B model generated code that assumed the wrong data shape

## Symptom

Asking the Analytics Agent (local model, not OpenRouter) "How many meetings
are there, and what is the average transcript length in words?" reliably
failed:

```python
# Calculate average word count per meeting
average_word_count = sum(word_count for _, _, word_count in data) / len(data)
```

```
Traceback (most recent call last):
  File "/tmp/tmp3pkh982r/runner.py", line 16, in <module>
    exec(code, sandbox_globals)
  File "<string>", line 5, in <module>
  File "<string>", line 5, in <genexpr>
ValueError: too many values to unpack (expected 3)
```

`data` is a list of **dicts** (`{"filename", "transcript", "language",
"word_count"}`), not a list of 3-element tuples — the generated code tried
to unpack each dict by iterating it directly (which yields its *keys*, one
string at a time) into three variables, which fails immediately. This was
first spotted by inspecting a Playwright screenshot of the Sandbox page
(`docs/screenshots/04-sandbox.png`, pre-fix) taken during documentation —
the visible stack trace made the bug obvious at a glance.

Reproduced deterministically: the local model's generation uses
`do_sample=False` (`ml/llm.py::_generate_local`), so the exact same wrong
code came back on 3/3 repeated identical requests — this was not a one-off
sampling fluke.

## Root cause

`routers/sandbox.py`'s `SYSTEM_PROMPT` told the model the shape of each
record (`{"filename": str, ...}`) but never said *how to iterate the list*
or explicitly ruled out tuple-unpacking. `Qwen2.5-0.5B-Instruct` is a very
small model (494M parameters) — it correctly understood "there is a list of
records with these fields" but, without a concrete usage example, filled in
a plausible-looking-but-wrong iteration idiom (`for _, _, word_count in
data`) that would be correct for a list of 3-tuples but not for a list of
dicts. The OpenRouter path (`qwen/qwen3-8b`, 8B parameters) did not exhibit
this failure on the same request — small local models are meaningfully more
prone to this class of mistake than the larger opt-in cloud model, which is
itself a genuine, useful illustration of the local-vs-cloud trade-off this
project's Sandbox page exists to demonstrate.

## Fix applied

Strengthened `SYSTEM_PROMPT` in `backend/app/routers/sandbox.py`:
explicitly stated "`data` is NOT a list of tuples — always access fields by
key... never by unpacking positions", and added one concrete correct-usage
example (`sum(r['word_count'] for r in data) / len(data)`). Small, targeted
prompt-engineering fix — no change to the sandbox's execution/isolation
code, which was never the problem here.

## Verification

Rebuilt the image, restarted the container, and re-ran the *exact* same
request 3 times against the local model: all 3 now produce correct,
working code (`sum(record['word_count'] for record in data) / len(data)`)
with real output (`Total number of meetings: 3` /
`Average word count per meeting: 14.67 words`), `exit_code: 0`. Re-ran the
full `verify_e2e.sh` afterward — 12/12 still pass. The sandbox screenshot
was recaptured to reflect the corrected behavior.

## What to study if this is new to you

- **A code-execution sandbox being secure and the generated code being
  *correct* are two independent properties.** The subprocess/resource-limit
  isolation worked exactly as designed here — it safely caught the
  `ValueError` and returned it as `stderr` with a non-zero exit code rather
  than crashing the request or the container. The bug was entirely in what
  code got generated, one layer up.
- **Small local LLMs need more explicit, example-driven prompts than large
  ones to reliably get data-shape details right** — this is a genuine,
  observable capability gap (not a bug in the model), and a good concrete
  example for why this project intentionally shows both a local and a cloud
  code-gen path side by side rather than picking one.
- **A screenshot taken for documentation purposes can double as a real bug
  report.** This issue was found by looking at the *rendered UI*, not by
  reading code — a reminder that "does it actually work when you use it
  through the real interface" catches things a code review alone won't.
