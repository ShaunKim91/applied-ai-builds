# Issue 06 — The audit trail's own "how long did this take" column is always 0

**Found**: while pulling a real example of the OpenRouter escalation call for this build's history
log, queried the admin Audit Log API directly (`GET /api/admin/audit-log`) for the just-made
`agent.escalate` entry. Its `latency_ms` field read `0.0` — for a call that, per the same E2E run's
own timer, took 33.4 real seconds.

## Root cause

Every `log_action()` call site in the backend passes `latency_ms=0.0` as a literal, or omits the
argument and takes `audit.py`'s own `latency_ms: float = 0.0` default:

- `routers/agent.py`'s `escalate_run()` — logs `agent.escalate` right after the real,
  multi-second `llm.escalate_to_cloud()` HTTP call returns, but never timed that call.
- `routers/agent.py`'s `_finalize()` — logs `agent.run` once a stream ends, but never timed the
  run.
- `routers/approvals.py`'s `decide()` — logs `approval.decide` with no `latency_ms` at all (falls
  back to the same 0.0 default).

`models.AuditLog.latency_ms` and `routers/admin.py`'s `GET /api/admin/audit-log` (which returns
`"latency_ms": round(l.latency_ms, 1)`) both exist specifically to surface this number — the
column's own docstring in `models.py` says the audit log records "who, what, how long,
success/failure" — but no code path in the entire project ever measures a real value for it. Every
row, for every action, always reads exactly `0.0`, regardless of whether the underlying call took
2ms or 33 real seconds.

**Why this stayed invisible**: `frontend/src/pages/Admin.tsx` types `latency_ms: number` on its
`AuditEntry` interface but never actually renders it anywhere in the Audit Log tab's JSX — so
nothing in the UI ever surfaced the wrong number to make it look suspicious. The value existed
correctly end-to-end at the type level and the API-response level; only the two things that would
have ever made it *useful* (a real measurement, and a real render) were both missing.

## Fix

- `routers/agent.py`'s `escalate_run()` now wraps the `llm.escalate_to_cloud()` call with
  `time.perf_counter()` and logs the real elapsed milliseconds.
- `routers/agent.py`'s `_finalize()` now computes the run's real total wall-clock duration as
  `(run.updated_at - run.created_at).total_seconds() * 1000` — a run's own start/finish timestamps
  already exist for the stale-run reaper (issue-03) and are the semantically correct measurement
  for "how long did this whole agent run take," not just its last step.
- `routers/approvals.py`'s `decide()` was left as `0.0` deliberately, not silently: an approval
  decision's own "latency" (how long an admin took to review it) isn't a meaningful system
  performance metric the same way an AI call's duration is, so a comment now says so explicitly
  rather than leaving another unexplained zero.

## Verification

- Re-ran the OpenRouter escalation E2E step and the calculator-run E2E step on the fixed build,
  then queried `GET /api/admin/audit-log` directly: the `agent.escalate` row now reads a real
  non-zero millisecond value consistent with that step's own reported E2E duration; the `agent.run`
  row for a multi-step run reads a real duration consistent with its step count and the model's
  known per-token generation speed, rather than `0.0`.
- Re-ran `verify_e2e.py` (16/16 — no existing check asserted on `latency_ms`'s value, so, like
  issue-04, this was invisible to the automated suite and could only be caught by actually reading a
  real API response rather than trusting the check's pass/fail alone).
