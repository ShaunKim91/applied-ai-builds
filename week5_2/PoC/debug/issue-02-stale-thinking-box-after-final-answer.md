# Issue 02 — The Final Answer step doesn't participate in the normal step lifecycle (two symptoms)

**Root cause (shared)**: `agent/orchestrator.py`'s ReAct loop emits a `step_complete` event for the
two intermediate step kinds — `thought_action` and `observation` — but the terminal **Final Answer**
step never gets one: once `"Final Answer:"` is detected in the generation, the loop persists the
step directly and yields a `done` event (the `"Final Answer:" in gen` branch), skipping
`step_complete` entirely. The frontend was written assuming every step kind follows the same
`step_complete` → later-shown-in-the-trace lifecycle, so this one exception surfaced two distinct,
separately-observed symptoms.

## Symptom 1 — stale "thinking" box on a fresh, live run

**Found**: during Playwright screenshot capture — after a calculator run completed live, the screen
kept showing a stale "Thinking…" box with the model's raw, uncleaned text (including the literal
"Final Answer: The result of 88 * 4 is 352." line) and a permanently-blinking cursor, duplicated
alongside the correctly-rendered "✓ Final Answer" card below it. Directly observed persisting
unchanged for 30+ seconds after the run had genuinely finished — not a transient rendering delay.

`frontend/src/pages/Console.tsx`'s `send()` handler only cleared `streamingText` inside its
`step_complete` branch — never inside its `done` branch. For every OTHER stopping condition
(guardrail stop, awaiting approval), a `step_complete` had already fired first and cleared the
buffer before `done` arrived; only the Final Answer path — the normal, successful completion case —
hit this gap.

**Fix**: `Console.tsx`'s `done` handler now unconditionally clears `streamingText` before setting
the final status/answer, regardless of which stopping condition was reached.

**Verification**: reproduced directly — ran a fresh calculator query, polled the rendered DOM every
second for 30 seconds after completion. Before the fix, the stale box with the blinking cursor was
still present unchanged at every poll. After the fix, `streamingText` clears the moment `done`
arrives, leaving only the correct "✓ Final Answer" card.

## Symptom 2 — the final answer renders twice when reopening a past run

**Found**: while capturing the dark-mode screenshot variant — reopening an already-completed run
from the sidebar showed the answer **twice**: once as an ordinary "FINAL ANSWER · STEP 2" trace
card (in the same list as Thought/Action/Observation), and again in the dedicated "✓ Final Answer"
card below it.

The backend's `GET /api/agent/runs/{id}` correctly returns the full persisted trace, which includes
the `final_answer`-kind `AgentStep` row `_persist_step()` wrote when the run completed (needed for a
complete audit record) — but `Console.tsx`'s `openRun()` set that full list directly as `steps`,
then ALSO rendered the same run's `final_answer` field in the dedicated card, with nothing excluding
the redundant step. The live-streaming path never hit this, precisely because of this issue's shared
root cause: no `step_complete` ever arrives for the Final Answer step during a live run, so `steps`
never contains one there — only the *reload* path could double up.

**Fix**: `openRun()` now filters `kind !== "final_answer"` out of the loaded steps before rendering,
so the dedicated card remains the single place a completed run's answer is shown, on both the live
and reloaded paths.

**Verification**: reproduced directly — opened a completed run from the sidebar, confirmed the
answer appeared twice before the fix; rebuilt the frontend, reopened the same run, confirmed it now
appears exactly once. Re-captured `docs/screenshots/02-console.png` and
`docs/screenshots/07-console-dark.png` on the fully-fixed build — see `../history/v1.0.0.md`.
