# Issue 04 — "morning"/"afternoon" preference silently never matched the fixed callback-slot table

**Severity**: Low (no crash; the deterministic tool quietly fell back to "list everything" instead of
actually filtering — the memory-conditioned auto-fill still looked correct in casual testing only
because the LLM's own reply narrative happened to pick a sensible slot from the unfiltered list)
**Status**: Fixed, covered by `verify_e2e.py::step_memory_conditioned_autofill`

## Symptom (actually observed)

A caller stated a preference for morning callbacks (extracted into `MemoryFact` as
`preferred_callback_window = "morning"`); a later turn asking for a billing callback slot correctly
auto-filled that value into `check_callback_availability`'s `preferred_window` argument (Issue 02's
sibling mechanism working as intended) — but the tool's own response was always the full unfiltered
slot list, never the single matching morning slot the auto-fill was supposed to surface.

## Root cause

`chains/tools.py::check_callback_availability()`'s original match was a literal substring check:
`preferred_window.lower() in s.lower()`. The fixed slot table is stamped `"Tomorrow 10:00 AM"`,
`"Tomorrow 2:00 PM"`, etc. — the word `"morning"` never appears in an `"AM"`-stamped string, so the
match never fired, regardless of how correctly the auto-fill had supplied it.

## Fix

Added `_slot_period()`: classifies each fixed slot as `"morning"` or `"afternoon"` by checking for
`"AM"` in the stamp, and the match now also accepts `pref in _slot_period(s)` alongside the original
literal substring check — so both a caller's natural "morning"/"afternoon" phrasing and a literal time
string both resolve correctly.

## How this was found

Direct manual testing of the memory-conditioned auto-fill scenario end-to-end — noticed the tool's own
returned text never actually narrowed to one slot despite the correct value visibly being auto-filled
into the request. A quick standalone call to `check_callback_availability("billing", "morning")`
confirmed the match silently fell through to the unfiltered branch every time.
