# Issue 03 — A run whose stream is abandoned mid-flight stays "RUNNING" forever

**Found**: while re-investigating debug/issue-02's fix — a screenshot script step that waited for
the text `"Final Answer"` to appear resolved too early (see "Why this was found" below), then
navigated to a new page mid-generation. A later, unrelated API check
(`GET /api/agent/runs`) showed that run permanently stuck at `status: "RUNNING"`,
`step_count: 1`, `final_answer: ""` — long after the browser session that started it was gone.

## Root cause

A `StreamingResponse`'s generator (`agent/orchestrator.py::run_react_loop`) is only advanced when
something actually consumes the stream. If the client disconnects mid-stream (closes the tab,
navigates away, or — as in the screenshot script's original bug — a `page.goto()` call aborts the
in-flight `fetch()`), Starlette simply stops calling `.__anext__()` on the generator. There is no
exception raised inside it to catch; the generator is just never resumed again. Whatever state was
committed up to that point (e.g., after the first Thought→Action→Observation cycle, before the
second cycle that would have produced the Final Answer) is the state that run is stuck at,
permanently: it can never complete (nothing is driving it), never be escalated
(`/escalate` requires `STOPPED_STEP_LIMIT` or `COMPLETED`), never appear in History (never embedded,
since `_finalize()` never runs), and permanently skews the Dashboard's run-count/analytics.

**Why this was found via a screenshot-script bug, not a "real" abandoned tab**: the script waited
on `text=/Final Answer/` becoming visible, but that literal substring is part of the *model's own
raw generated text* the moment it starts writing the "Final Answer:" line — visible well before
generation (let alone the backend's post-completion persistence) actually finishes. The script then
proceeded immediately and navigated to a new page, which is exactly the abandonment scenario a real
user closing a tab mid-response would also trigger. The underlying vulnerability was real and would
affect actual users, independent of how it was first noticed.

## Fix

`routers/agent.py` adds a lightweight, lazy "reap stale runs" step (`_reap_stale_runs()`), run at the
top of both `GET /api/agent/runs` and `GET /api/agent/runs/{id}` (the same "fix lazily on next real
request" philosophy this project's bootstrap isolation already uses) — any run still `RUNNING` with
no update in the last 180 seconds is marked `FAILED` with an honest explanation
("This run was abandoned..."), rather than staying invisible and unrecoverable forever.

This required a second, smaller real fix: `models.AgentRun.updated_at` had `default=utcnow` but no
`onupdate=utcnow` — meaning it was stamped once at creation and never actually advanced on later
updates, so a staleness check comparing "now" against `updated_at` would have misfired immediately
on any run at all. Added `onupdate=utcnow` so the column does what a staleness check needs.

## Verification

- Reproduced directly: started a real run over HTTP, aborted the connection mid-stream (closed the
  client before the second generation step), confirmed via `GET /api/agent/runs` that the row was
  stuck at `RUNNING` with `step_count: 1`.
- After the fix: waited past the 180s threshold, re-queried `GET /api/agent/runs`, confirmed the
  same run now reads `status: "FAILED"` with the explanatory message, rather than `RUNNING` forever.
- Fixed the screenshot script itself so it no longer reproduces the abandonment scenario by
  accident — waits for a terminal status badge (e.g. `"✓ Final Answer"`) instead of a raw text
  substring the model's own output can produce mid-stream. The first replacement attempted ("wait
  for the Run button to re-enable") turned out to be its own dead end — see debug/README.md's
  third non-bug finding and issue-04 for how that was untangled. See also
  `prompts/vibe_coding_prompts.md`.
- Re-ran `verify_e2e.py` (16/16 — none of its steps abandon a stream mid-flight, so this wasn't a
  path the automated suite exercised) and re-captured all screenshots on the fixed build — see
  `../history/v1.0.0.md`.
