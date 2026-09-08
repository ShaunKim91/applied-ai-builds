# Issue 01 — A naive guardrail check order mislabels unauthorized-tool attempts

**Found**: while researching this problem space during planning (not a bug in our own code — a
conceptual pitfall identified during design, then deliberately avoided in Cradle from the start,
with a dedicated regression test).

## Symptom

The intuitive, correct guardrail check order for an agent tool call is: **step limit → permission →
cost cap → HITL**. Permission has to be checked before cost, because an unauthorized tool call is a
security event, not a budget event — it should never be allowed to "spend" against the cost cap or
be explained away as a budget stop.

A naive first-pass implementation of this pattern is easy to get wrong: it's tempting to check the
cost cap right after the step limit (both are simple numeric comparisons) and only check tool
permission afterward. That ordering looks harmless until you consider what happens when both
conditions are true at once.

## Root cause

Trace the scenario by hand: with a cost cap of 15, after spending 5 and then 10 (spent → 15), a call
to a tool that was never on the allowlist arrives. In the naive (cost-before-permission) ordering,
the cost check fires first and the call is stopped and labeled as a cost-cap event — the permission
check never even runs. A security-relevant "someone tried an unauthorized tool" event gets
mislabeled as an unrelated budget event, directly undermining the audit trail's ability to
distinguish real anomalies (unauthorized access attempts) from routine budget stops.

## Fix

Cradle's `backend/app/agent/guardrails.py::check_guardrails()` implements the correct order:
step limit → **permission → cost cap** → HITL. This is a deliberate design decision made from the
start — permission is always checked before cost, so an unauthorized-tool call is always labeled
`BLOCKED_PERMISSION`, never miscategorized as a cost-cap stop, regardless of how much budget has
already been spent.

## Verification

- `verify_e2e.py`'s `step_guardrail_order_regression` reproduces exactly this scenario
  (`cost_cap=15`, `spent=15`, calling an unauthorized tool) directly against
  `agent/guardrails.check_guardrails()` and asserts `BLOCKED_PERMISSION`, not `STOPPED_COST_CAP`.
  Passed on every run this build (see `../history/v1.0.0.md`).
