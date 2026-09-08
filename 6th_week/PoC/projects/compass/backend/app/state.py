"""Tiny shared process-state module for the background bootstrap flow.

Kept separate from main.py so routers (e.g. health.py) can import it without
a circular import on main.py itself. Individual model-loaded flags are NOT
duplicated here — health.py reads each ml module's real singleton state
directly (the same technique routers/admin.py uses), so there is exactly one
source of truth and no risk of this state drifting from reality (a model can
also be lazy-loaded by an ordinary user request, not just by the bootstrap
thread below).

bootstrap_step_errors is a per-step map: each startup step (3 local model
loads + a live web-search connectivity check) is isolated so a transient
failure in ONE step (e.g. `ddgs`'s live search being rate-limited on first
boot) can never take the others down with it — every step is attempted
regardless of whether an earlier one failed. See 4th_week/PoC's debug/issue-01
for a real, previously-encountered example of exactly this kind of
cascading failure, which is what this isolation exists to prevent.
"""
import threading

bootstrap_complete = threading.Event()
bootstrap_step_errors: dict[str, str] = {}  # step name -> error message, only for steps that failed

# Set once at bootstrap by main.py's warm step, then refreshable any time via
# GET /api/admin/web-search-check. Distinct from bootstrap_step_errors
# because a ddgs failure is an *expected, handled* outcome (mock fallback),
# not a bootstrap error — this just reports which mode is actually live.
last_web_search_check: dict | None = None
