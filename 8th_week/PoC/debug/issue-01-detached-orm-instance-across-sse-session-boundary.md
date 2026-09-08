# Issue 01 — Detached ORM instance crashed the second half of every message turn

**Severity**: High (crashed every single message send once a memory-fact conflict occurred)
**Status**: Fixed, regression-tested (`verify_e2e.py::step_memory_conflict_guardrail`)

## Symptom (actually observed, real traceback)

Sending a second message in a case that had just produced a memory-fact conflict crashed with:

```
sqlalchemy.orm.exc.DetachedInstanceError: Instance <MemoryConflictLog at 0x11bb4db50> is not
bound to a Session; attribute refresh operation cannot proceed
```

raised from `chains/orchestrator.py::finalize_turn()` at `conflict.resolution == "pending_confirmation"`.

## Root cause

`routers/cases.py::send_message()` opens its own `SessionLocal()`, calls `orchestrator.prepare_turn()`
with it, then closes it in a `finally` block — **before** the `StreamingResponse` generator body (which
calls `orchestrator.finalize_turn()` in a *second*, fresh `SessionLocal()`) ever starts running. Early
versions of `TurnContext` carried the live `MemoryConflictLog` ORM rows (and the `CallerCase` row)
created in the first session straight through to `finalize_turn()`. By the time `finalize_turn()` tried
to read `conflict.resolution`, the object was detached from any session and SQLAlchemy's default
expire-on-commit behavior needed a live session to re-fetch the value — which no longer existed.

This is the exact session-lifetime pitfall Threshold's own `agent/orchestrator.py` docstring already
warns about ("a dependency-injected session closes when the route handler *returns*, which happens
before a StreamingResponse generator body has finished running") — encountered here in a different
shape (two separate `SessionLocal()` sessions, not one `Depends(get_db)` session) despite having read
that exact warning while designing this build.

## Fix

`TurnContext.conflicts` now holds plain `dict`s (`field_name`, `resolution`) extracted from the ORM
rows **while `prepare_turn()`'s own session is still open**, not the live rows themselves.
`TurnContext.case_id` replaces the live `CallerCase` reference entirely; `finalize_turn()` re-fetches
the case via `db.get(models.CallerCase, ctx.case_id)` in **its own** session before touching any of its
attributes. No ORM object now crosses the `prepare_turn()` / `finalize_turn()` session boundary.

## How this was found

Found by direct manual testing (not by `verify_e2e.py`, which was written afterward specifically to
catch a regression of this) — a 3-turn conversation that organically produced a memory-fact conflict
(the router legitimately disagreed with itself about the caller's name across turns) crashed the very
next message send. Reproduced deterministically by manually seeding a `MemoryFact` +
`MemoryConflictLog` row and sending one message, which is now `verify_e2e.py`'s
`step_memory_conflict_guardrail`.
