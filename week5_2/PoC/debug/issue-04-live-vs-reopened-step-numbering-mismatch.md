# Issue 04 — The same run shows different step numbers live vs. reopened

**Found**: while visually spot-checking the fixed screenshot set (see issue-03/README for why
screenshots are checked, not just assumed correct once the script exits cleanly) — comparing
`02-console.png` (a fresh calculator run, captured immediately after it completed live) against
`07-console-dark.png` (the *same* completed run, reopened from the sidebar and re-screenshotted in
dark mode) showed the Observation card labeled `OBSERVATION · STEP 2` in the first and
`OBSERVATION · STEP 1` in the second — one persisted run, two different displayed step numbers for
the identical card, depending only on how it was viewed.

## Root cause

`agent/orchestrator.py` numbers a whole ReAct cycle — one `thought_action` plus its paired
`observation` — with a single shared `step_count` value (`step_count` only increments once per
`while True:` iteration, at the top of the loop; both `_persist_step()` calls inside that iteration
use the same value). So the backend's own persisted data for a one-cycle run reads
`thought_action.step_number == 1` and `observation.step_number == 1` — which is exactly what
`openRun()` renders when reopening a past run, since it uses the persisted `step_number` values
as-is.

The **live** streaming path never had access to that number: `agent/orchestrator.py`'s
`step_complete` events carried `{"kind": ..., "content": ...}` only — no `step_count` field, even
though the loop already had the correct value in scope at every yield point. Without it,
`frontend/src/pages/Console.tsx`'s `send()` handler invented its own number instead:
`{ step_number: prev.length + 1, ... }` — a plain running count of *cards rendered so far*, treating
`thought_action` and `observation` as two separate "steps" (1 and 2) rather than one cycle. The two
numbering schemes agreed only by coincidence on single-step runs' first card, and diverged from the
second card of any run onward.

## Fix

- `agent/orchestrator.py`: added `"step_count": step_count` to all three `step_complete` yield sites
  (the `resume_injection` post-approval event, the `thought_action` event, and the `observation`
  event) — the value was already in scope; it just wasn't being sent.
- `frontend/src/pages/Console.tsx`: `send()`'s `step_complete` handler now reads
  `event.step_count ?? prev.length + 1` instead of always deriving its own count, so a live run and
  a reopened run number the exact same persisted cycle identically. The `?? prev.length + 1`
  fallback is defensive only (an older backend build omitting the field), not part of the intended
  path going forward.

## Verification

- Reproduced directly by comparing the two screenshots above — confirmed the mismatch was real, not
  a rendering artifact, by cross-referencing both against a direct `GET /api/agent/runs/{id}` query
  for the same run, which showed both persisted `AgentStep` rows at `step_number: 1`.
- After the fix: rebuilt the image, re-ran the same calculator query fresh, confirmed the live view's
  Observation card now also reads `STEP 1`; reopened the run and confirmed it still reads `STEP 1` —
  both paths agree.
- Re-ran `verify_e2e.py` (16/16 still pass — none of the 16 checks assert on displayed step *labels*,
  only on final answers/statuses/guardrail outcomes, so this bug was invisible to the automated
  suite and could only be caught by actually looking at rendered output). This is itself a real
  observation worth keeping: automated API-level checks did not — and structurally could not — catch
  a client-side display/derivation bug like this one; only visual inspection did.
- Re-captured the full screenshot set on the fixed build — see `../history/v1.0.0.md`.
