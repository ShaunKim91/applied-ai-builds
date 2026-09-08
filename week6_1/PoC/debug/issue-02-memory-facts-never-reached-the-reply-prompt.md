# Issue 02 — Structured memory was extracted and persisted, but the assistant couldn't actually use it

**Severity**: High (the product's own headline feature didn't do anything beyond decorate a sidebar)
**Status**: Fixed, regression-tested (`verify_e2e.py::step_memory_recall_regression`)

## Symptom (actually observed)

A real 3-turn test conversation: the rep states the caller's name and policy number, looks up the
account, then asks "What was the caller's name again?" — a question one turn past where the raw
transcript window would normally still hold it, and (in this run) also right after the router mis-
routed the recall question to `lookup_caller_account` with a nonsense `{"name": ""}` argument (a
separate, expected small-model routing miss, gracefully absorbed as a `Tool result: Error - ...`
line). The final reply: *"The caller's name is not provided in your last message."* — despite the name
being correctly extracted and sitting, correctly, in that case's `MemoryFact` rows the whole time.

## Root cause

`chains/orchestrator.py::prepare_turn()` built the reply-generation message list as
`windowed_messages(...) + [HumanMessage(combined_content)]` — the raw, windowed transcript only.
`MemoryFact` rows were written (by `chains/extraction.py`) and read back by the Workspace UI's sidebar
and by `_autofill_args()` for a handful of tool arguments, but were **never included in the prompt
handed to the local model for composing its actual reply**. Persisting structured memory and showing
it in a sidebar is not the same as the assistant being able to use it — this build had built the
former without the latter, which only became visible once a real recall question landed outside the
raw window.

## Fix

Added `chains/orchestrator.py::_facts_system_prompt()`: builds a compact "Known case facts so far"
block from the case's current `MemoryFact` rows and prepends it to `REPLY_SYSTEM_PROMPT` as a
`SystemMessage`, injected into `reply_messages` every turn — not just when the router decides a tool
is needed. This is what actually makes the "index card" mechanism functional rather than cosmetic.

## How this was found

Direct manual testing of a natural multi-turn conversation, immediately after fixing Issue 01 in the
same debugging session — re-running the same kind of scenario surfaced this as a second, independent
gap. Confirms this project's own standing lesson (see Threshold's `vibe_coding_prompts.md` Phase 4):
after a fix passes its own test, actively construct the next plausible failure this build's own new
surface area (structured memory, not present in either Verity or Threshold) could still have.
