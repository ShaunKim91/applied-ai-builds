# Debug Log — Threshold (Week5_2 PoC_v2)

Real issues only, found via actual manual (Playwright) browser testing and direct trace inspection
— never fabricated. Each entry links a symptom actually observed to a root cause actually confirmed
in the code.

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-quoted-string-arguments-broke-tool-lookups.md) | The model naturally quoted a string tool-argument (`lookup_claims_procedure("subrogation")`); nothing stripped the quote characters, so a real, existing procedure lookup silently failed and the agent told the user it didn't exist | Medium (a real, user-visible false negative) | Fixed at the parser, regression-tested |

## What this build carried forward correctly from the start (not rediscovered)

Unlike the predecessor Cradle PoC, this build did not reproduce any of Cradle's own six real bugs —
each lesson was applied proactively from the first line of code, not discovered again:

- **The corrected guardrail check order** (step limit → permission → cost cap → HITL) — implemented
  correctly from the start, with a direct regression test reproducing the common guardrail-order
  bug scenario found in naive implementations of this pattern (`step_guardrail_order_regression`).
- **The stale-run reaper** (`_reap_stale_runs()`) and the `AgentRun.updated_at` `onupdate=utcnow`
  fix it depends on — both present from the first commit, with a direct regression test
  (`step_stale_run_reaper_regression`) rather than waiting to observe the failure live.
- **Consistent step numbering** between a live-streaming run and a reopened one — `step_complete`
  events include the real backend `step_count` from the start, avoiding the live-vs-reopened
  mismatch Cradle shipped and later fixed.
- **The Final Answer step's `streamingText` clearing** and **`final_answer`-kind step filtering on
  reopen** — both present from the first version of `Console.tsx`.

Only one genuinely new failure mode was found this round, and it wasn't one Cradle's own build had
occasion to hit: Cradle's tool arguments were either purely numeric or simple comma-separated pairs
the model happened not to quote during that build's own testing. Threshold's richer, more
string-heavy tool set (procedure lookups by keyword) gave the model more reason to reach for quoted
string syntax, surfacing a real gap the parser needed to handle regardless of which specific build
first exposed it.

## A real finding that is not a product bug

While iterating on the fix above, re-running `verify_e2e.sh` repeatedly in quick succession against
the *same* long-lived container (rebuilding the image but not the volumes between attempts)
eventually produced a run with a spurious `BLOCKED_PERMISSION` on a tool the suite's own earlier
step had already used successfully, followed by cascading `429 Too Many Requests` errors on several
later auth-related steps. This is expected, not a bug: the rate limiter (`rate_limit.py`) and the
guardrail settings are both real, persistent state living in the same container's process/database
across repeated invocations — running the auth-heavy suite several times within its own 60-second
rate-limit window will legitimately exhaust it, exactly as designed. A full clean rebuild
(`docker compose down -v`) reset all of it and the same 26/26 suite passed cleanly on the very next
attempt, confirming this was a testing-cadence artifact of this debugging session, not a defect in
the rate limiter or the guardrail persistence themselves.
