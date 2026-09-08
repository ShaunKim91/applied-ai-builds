# Issue 05 — The E2E stale-run regression test polluted the real admin account

**Found**: while visually spot-checking the final screenshot set — `01-dashboard.png` (taken
immediately after logging in as `admin@cradle.local`, before the screenshot script's own console
run had even started) already showed **"Agent runs: 1"**, and the Console sidebar in later
screenshots listed a run titled `"(regression test — simulated abandoned run)"` sitting in the real
admin account's own Past Runs list. On a container just rebuilt from empty volumes, the admin
account should have zero runs until the screenshot script (or a real user) creates one.

## Root cause

`verify_e2e.py`'s `step_stale_run_reaper_regression()` (the regression test for issue-03) needs to
attach its synthetic "stale RUNNING row" to *some* existing user, and picked one with
`db.query(User).first()` — the row with the lowest id. Because the seeded admin account is always
created before any test user signs up (`main.py`'s startup seeding runs before `step_signup()`'s
`POST /api/auth/signup`), `.first()` reliably resolved to the admin, not to the disposable
`e2e-<timestamp>@example.com` account the rest of the suite already uses for exactly this reason
(so its test data doesn't land in a real account). The synthetic run — and the "FAILED" state the
reaper correctly converts it to a few lines later in the same test — was attributed entirely to
the real operator/demo account.

This matters beyond cosmetics: the admin account is the one used to operate, administer, and demo
Cradle. Anyone running `./scripts/verify_e2e.sh` against a long-lived instance (not just a
just-wiped one) would have a fake, confusingly-labeled run silently appear in their own history and
inflate their own Dashboard's "Agent runs" count on every test run, indistinguishable at a glance
from real usage.

## Fix

`step_signup()` now stashes the email it just created in the test's shared `_ctx` dict.
`step_stale_run_reaper_regression()` looks up that specific user by email instead of blindly taking
the first row in the table, so its synthetic data lands in the same throwaway identity every other
step in the suite already uses — never in the real admin account.

## Verification

- Reproduced directly: before the fix, `GET /api/admin/analytics` (as admin) and the Dashboard's own
  numbers showed the phantom run immediately after any `verify_e2e.sh` run, on an otherwise-untouched
  admin account.
- After the fix: re-ran a full clean rebuild (`docker compose down -v`, rebuild, cold model warm-up,
  `verify_e2e.sh`) and confirmed the admin account's Dashboard read "Agent runs: 0" immediately after
  the suite passed 16/16, with the synthetic regression row instead attached to that run's own
  `e2e-*` test account — invisible to the admin, exactly as intended.
- Re-captured the full screenshot set on this fixed, clean build — see `../history/v1.0.0.md`.
