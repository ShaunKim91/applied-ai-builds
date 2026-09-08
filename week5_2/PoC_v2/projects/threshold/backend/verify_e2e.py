"""End-to-end smoke test for Threshold.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming the streamed agent-run response as
a real client would, and actually running a paused-for-approval run through
to resumption. Also exercises the new commercial-grade features (rate
limiting, account lockout, refresh-token rotation, CSRF protection,
hash-chained audit-log tamper detection) shared with Verity's architecture,
plus Threshold-specific regressions (the corrected guardrail order, the
amount-aware HITL threshold, the stale-run reaper).

Run from inside the container:
    docker compose exec -T app python verify_e2e.py
or via the convenience wrapper:
    ./scripts/verify_e2e.sh
"""
import json
import os
import sys
import time

import requests

BASE = f"http://localhost:{os.environ.get('PORT', '8000')}"
session = requests.Session()
results: list[tuple[str, bool, float, str]] = []
_ctx: dict = {}


def check(name: str, fn) -> None:
    start = time.perf_counter()
    try:
        fn()
        results.append((name, True, time.perf_counter() - start, ""))
    except Exception as exc:  # noqa: BLE001
        results.append((name, False, time.perf_counter() - start, str(exc)))


def csrf_headers() -> dict:
    token = session.cookies.get("csrf_token")
    return {"X-CSRF-Token": token} if token else {}


def _admin_session():
    admin_session = requests.Session()
    r = admin_session.post(f"{BASE}/api/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "admin@fenwickmutual.example"), "password": os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")}, timeout=15)
    assert r.status_code == 200, r.text
    return admin_session, {"X-CSRF-Token": admin_session.cookies.get("csrf_token")}


def step_health():
    r = session.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200 and r.json()["status"] == "ok"


def step_wait_for_warm():
    deadline = time.time() + 1200
    last_print = 0.0
    while time.time() < deadline:
        r = session.get(f"{BASE}/api/health/ready", timeout=10)
        body = r.json()
        if body.get("all_warm"):
            return
        if time.time() - last_print > 15:
            not_yet = [k for k, v in body.get("models", {}).items() if not v]
            print(f"    ... still warming up: {', '.join(not_yet) or 'unknown'}")
            last_print = time.time()
        time.sleep(3)
    raise AssertionError("models did not finish warming up within 20 minutes")


def step_signup():
    email = f"e2e-{int(time.time())}@fenwickmutual.example"
    r = session.post(f"{BASE}/api/auth/signup", json={"email": email, "password": "TestPass123!", "display_name": "E2E Bot"}, timeout=15)
    assert r.status_code == 200, r.text
    _ctx["email"] = email


def step_me():
    r = session.get(f"{BASE}/api/auth/me", timeout=10)
    assert r.status_code == 200 and r.json()["email"] == _ctx["email"]


def step_csrf_blocks_missing_header():
    r = requests.post(f"{BASE}/api/agent/runs", json={"question": "should be blocked"}, cookies=session.cookies.get_dict(), timeout=10)
    assert r.status_code == 403, f"expected 403 without CSRF header, got {r.status_code}"


def _consume_run_stream(resp):
    final = None
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: ") :])
        if event.get("done"):
            final = event
    return final


def step_safe_tool_run():
    r = session.post(f"{BASE}/api/agent/runs", json={"question": "What is 500 minus a $150 deductible? Use the estimate_claim_payout tool."}, headers=csrf_headers(), timeout=60, stream=True)
    assert r.status_code == 200, r.text
    final = _consume_run_stream(r)
    assert final is not None and final["status"] == "COMPLETED", f"expected COMPLETED, got {final}"
    assert "350" in final["final_answer"], f"expected the correct arithmetic answer, got: {final['final_answer']}"
    _ctx["safe_run_id"] = final["run_id"]


def step_quoted_argument_regression():
    """Direct unit check: a real bug found via manual testing — the model
    naturally quotes a string argument (lookup_claims_procedure("subrogation"))
    since the few-shot example only demonstrates a bare numeric argument.
    Every tool's own keyword matching stripped whitespace but not quote
    characters, so the literal quoted string never matched a real key.
    Fixed in tools.py's own clean_arg()/split_args() helpers (NOT in
    parse_action() — an earlier fix there handled this manifestation but
    broke a second one, see debug/issue-01), so this checks parse_action()
    passes the argument through untouched and the TOOL itself cleans it."""
    from app.agent.react_loop import parse_action

    action = parse_action('Thought: I should look this up.\nAction: lookup_claims_procedure("subrogation")')
    assert action is not None
    tool_name, arg = action
    assert tool_name == "lookup_claims_procedure"
    assert arg == '"subrogation"', f"expected parse_action() to pass the argument through unmodified, got {arg!r}"

    from app.agent.tools import lookup_claims_procedure

    result = lookup_claims_procedure(arg)
    assert "no procedure document found" not in result.lower(), f"expected a real match for the unquoted keyword, got: {result}"

    # Manifestation 2 of the same real bug: two SEPARATELY quoted,
    # comma-separated arguments — the more natural convention for a
    # multi-argument call, actually observed in a real run. An initial
    # fix (stripping quotes from the whole joined string before splitting)
    # handled manifestation 1 above but broke this one.
    from app.agent.tools import check_filing_deadline

    result2 = check_filing_deadline('"Belmont Bay", "2025-01-01"')
    assert "unknown jurisdiction" not in result2.lower(), f"expected the separately-quoted jurisdiction to resolve correctly, got: {result2}"
    assert "730 days" in result2, f"expected a real computed deadline (730-day period for Belmont Bay): {result2}"


def step_guardrail_order_regression():
    """Direct unit check reproducing the common guardrail-order bug
    scenario: an unauthorized tool call made when the cost cap is ALSO
    already exhausted must be logged as BLOCKED_PERMISSION (permission
    checked first), never STOPPED_COST_CAP."""
    from app.agent.guardrails import check_guardrails

    verdict = check_guardrails(
        "close_and_purge_claim_file",
        "CLM-0001",
        step_count=1,
        max_steps=6,
        allowed_tools={"estimate_claim_payout"},
        tool_cost={"close_and_purge_claim_file": 50},
        spent=150,
        cost_cap=150,
        hitl_tools=set(),
        payout_approval_threshold_usd=2500.0,
    )
    assert verdict.status == "BLOCKED_PERMISSION", f"expected BLOCKED_PERMISSION even with budget exhausted, got {verdict.status}"


def step_amount_aware_hitl_regression():
    from app.agent.guardrails import check_guardrails

    small = check_guardrails("issue_claim_payout", "CLM-1, 500", step_count=1, max_steps=6, allowed_tools={"issue_claim_payout"}, tool_cost={"issue_claim_payout": 35}, spent=0, cost_cap=150, hitl_tools={"issue_claim_payout"}, payout_approval_threshold_usd=2500.0)
    assert small.status == "ALLOWED", f"expected a $500 payout under the $2500 threshold to be ALLOWED, got {small.status}"

    large = check_guardrails("issue_claim_payout", "CLM-2, 9000", step_count=1, max_steps=6, allowed_tools={"issue_claim_payout"}, tool_cost={"issue_claim_payout": 35}, spent=0, cost_cap=150, hitl_tools={"issue_claim_payout"}, payout_approval_threshold_usd=2500.0)
    assert large.status == "AWAITING_APPROVAL", f"expected a $9000 payout over the $2500 threshold to require approval, got {large.status}"

    unparsable = check_guardrails("issue_claim_payout", "garbage-arg", step_count=1, max_steps=6, allowed_tools={"issue_claim_payout"}, tool_cost={"issue_claim_payout": 35}, spent=0, cost_cap=150, hitl_tools={"issue_claim_payout"}, payout_approval_threshold_usd=2500.0)
    assert unparsable.status == "AWAITING_APPROVAL", f"expected an unparsable amount to fail SAFE (require approval), got {unparsable.status}"


def step_stale_run_reaper_regression():
    import datetime as dt

    from app.database import SessionLocal
    from app.models import AgentRun, User
    from app.routers.agent import _reap_stale_runs

    db = SessionLocal()
    try:
        e2e_email = _ctx.get("email")
        assert e2e_email, "step_signup() must run before this check"
        user = db.query(User).filter(User.email == e2e_email).first()
        assert user is not None
        stale = AgentRun(org_id=user.org_id, owner_id=user.id, question="(regression test — simulated abandoned run)", status="RUNNING", step_count=1, messages_json="[]")
        db.add(stale)
        db.commit()
        db.refresh(stale)
        db.query(AgentRun).filter(AgentRun.id == stale.id).update({"updated_at": dt.datetime.utcnow() - dt.timedelta(seconds=181)})
        db.commit()
        _reap_stale_runs(db, user.org_id)
        db.refresh(stale)
        assert stale.status == "FAILED", f"expected the stale run to be reaped to FAILED, got {stale.status!r}"
        assert stale.final_answer
    finally:
        db.close()


def step_hitl_approve_flow():
    r = session.post(f"{BASE}/api/agent/runs", json={"question": "Issue a payout of $5000 for claim CLM-9001 using the issue_claim_payout tool."}, headers=csrf_headers(), timeout=60, stream=True)
    assert r.status_code == 200, r.text
    final = _consume_run_stream(r)
    assert final is not None and final["status"] == "AWAITING_APPROVAL", f"expected a $5000 payout to await approval, got {final}"
    approval_id = final["approval_request_id"]

    admin_session, admin_headers = _admin_session()
    r = admin_session.post(f"{BASE}/api/approvals/{approval_id}/decide", json={"approve": True}, headers=admin_headers, timeout=60)
    assert r.status_code == 200, r.text
    result = r.json()["run_result"]
    assert result is not None and result["status"] == "COMPLETED", f"expected the run to complete after approval, got {result}"
    assert "5000" in result["final_answer"] or "CLM-9001" in result["final_answer"], f"expected the real payout confirmation in the final answer: {result['final_answer']}"


def step_hitl_deny_flow():
    r = session.post(f"{BASE}/api/agent/runs", json={"question": "Issue a payout of $6000 for claim CLM-9002 using the issue_claim_payout tool."}, headers=csrf_headers(), timeout=60, stream=True)
    assert r.status_code == 200, r.text
    final = _consume_run_stream(r)
    assert final is not None and final["status"] == "AWAITING_APPROVAL", f"expected a $6000 payout to await approval, got {final}"
    approval_id = final["approval_request_id"]

    admin_session, admin_headers = _admin_session()
    r = admin_session.post(f"{BASE}/api/approvals/{approval_id}/decide", json={"approve": False, "reason": "exceeds examiner authority for a first review"}, headers=admin_headers, timeout=60)
    assert r.status_code == 200, r.text
    result = r.json()["run_result"]
    assert result is not None, "expected the run to resume and reach a terminal state after denial"


def step_guardrail_step_limit():
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/guardrails", json={"allowed_tools": ["estimate_claim_payout", "lookup_claims_procedure"], "max_steps": 1, "cost_cap": 150, "payout_approval_threshold_usd": 2500}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(f"{BASE}/api/agent/runs", json={"question": "Look up the total-loss auto procedure, then look up the subrogation checklist procedure, then estimate a payout of 500 minus 100."}, headers=csrf_headers(), timeout=60, stream=True)
    final = _consume_run_stream(r)
    assert final is not None and final["status"] in ("STOPPED_STEP_LIMIT", "COMPLETED"), f"expected a step-limited or fast-completing run, got {final}"

    r = admin_session.put(f"{BASE}/api/admin/guardrails", json={"allowed_tools": sorted(["check_filing_deadline", "lookup_policy_coverage", "estimate_claim_payout", "convert_reinsurance_currency", "lookup_claims_procedure", "issue_claim_payout"]), "max_steps": 6, "cost_cap": 150, "payout_approval_threshold_usd": 2500}, headers=admin_headers, timeout=10)
    assert r.status_code == 200


def step_guardrail_cost_cap():
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/guardrails", json={"allowed_tools": ["lookup_claims_procedure"], "max_steps": 6, "cost_cap": 5, "payout_approval_threshold_usd": 2500}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(f"{BASE}/api/agent/runs", json={"question": "Look up the subrogation checklist procedure."}, headers=csrf_headers(), timeout=60, stream=True)
    final = _consume_run_stream(r)
    assert final is not None and final["status"] in ("STOPPED_COST_CAP", "COMPLETED"), f"expected a cost-capped or fast-completing run, got {final}"

    r = admin_session.put(f"{BASE}/api/admin/guardrails", json={"allowed_tools": sorted(["check_filing_deadline", "lookup_policy_coverage", "estimate_claim_payout", "convert_reinsurance_currency", "lookup_claims_procedure", "issue_claim_payout"]), "max_steps": 6, "cost_cap": 150, "payout_approval_threshold_usd": 2500}, headers=admin_headers, timeout=10)
    assert r.status_code == 200


def step_history_search():
    r = session.post(f"{BASE}/api/history/search", json={"query": "claim payout deductible arithmetic"}, headers=csrf_headers(), timeout=30)
    assert r.status_code == 200, r.text
    matches = r.json()
    assert any(m["id"] == _ctx.get("safe_run_id") for m in matches), f"expected to find the earlier safe-tool run via semantic search, got {matches}"


def step_budget_blocks_zero():
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(f"{BASE}/api/agent/runs/{_ctx['safe_run_id']}/escalate", headers=csrf_headers(), timeout=15)
    assert r.status_code == 402, f"expected a 402 budget-cap block, got {r.status_code}"

    r = admin_session.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 1.0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200


def step_openrouter_real_call():
    r = session.post(f"{BASE}/api/agent/runs", json={"question": "What is the filing deadline for a loss in Belmont Bay on 2025-01-01? Use the check_filing_deadline tool."}, headers=csrf_headers(), timeout=60, stream=True)
    final = _consume_run_stream(r)
    assert final is not None, "expected the local run to reach a terminal state"
    run_id = final["run_id"]

    r = session.post(f"{BASE}/api/agent/runs/{run_id}/escalate", headers=csrf_headers(), timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model"], f"expected a real OpenRouter model name in the response: {body}"


def step_admin_audit_and_integrity():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/audit-log", timeout=10)
    assert r.status_code == 200 and len(r.json()) > 0
    r = admin_session.get(f"{BASE}/api/admin/audit-log/verify", timeout=10)
    assert r.status_code == 200 and r.json()["intact"] is True, f"expected an intact hash chain: {r.json()}"


def step_audit_tamper_detection_regression():
    from app.audit import verify_chain
    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        row = db.query(AuditLog).order_by(AuditLog.id.asc()).first()
        assert row is not None
        original_detail = row.detail
        db.query(AuditLog).filter(AuditLog.id == row.id).update({"detail": original_detail + " <tampered>"})
        db.commit()
        result = verify_chain(db)
        assert result["intact"] is False, "expected the hash chain to detect the tampered row"
        db.query(AuditLog).filter(AuditLog.id == row.id).update({"detail": original_detail})
        db.commit()
        result2 = verify_chain(db)
        assert result2["intact"] is True
    finally:
        db.close()


def step_rate_limit_regression():
    from fastapi import HTTPException

    from app.rate_limit import _check

    key = f"e2e-test-{time.time()}"
    for _ in range(3):
        _check(key, 3)
    try:
        _check(key, 3)
        raise AssertionError("expected the 4th call within the window to be rate-limited")
    except HTTPException as exc:
        assert exc.status_code == 429


def step_account_lockout():
    email = f"e2e-lockout-{int(time.time())}@fenwickmutual.example"
    r = requests.post(f"{BASE}/api/auth/signup", json={"email": email, "password": "RealPass123!", "display_name": "Lockout Test"}, timeout=15)
    assert r.status_code == 200, r.text
    for _ in range(5):
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "WrongPass000!"}, timeout=10)
        assert r.status_code == 401
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "RealPass123!"}, timeout=10)
    assert r.status_code == 423, f"expected the account to be locked, got {r.status_code}"


def step_refresh_rotation():
    login_session = requests.Session()
    r = login_session.post(f"{BASE}/api/auth/login", json={"email": _ctx["email"], "password": "TestPass123!"}, timeout=15)
    assert r.status_code == 200, r.text
    old_refresh = login_session.cookies.get("refresh_token")
    r = login_session.post(f"{BASE}/api/auth/refresh", timeout=10)
    assert r.status_code == 200, r.text
    new_refresh = login_session.cookies.get("refresh_token")
    assert new_refresh != old_refresh
    stale_session = requests.Session()
    stale_session.cookies.set("refresh_token", old_refresh)
    r = stale_session.post(f"{BASE}/api/auth/refresh", timeout=10)
    assert r.status_code == 401, f"expected a reused refresh token to be rejected, got {r.status_code}"


def step_status_page_public():
    r = requests.get(f"{BASE}/api/status", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("app", "uptime_seconds", "models_warm", "vector_store_reachable", "openrouter_configured"):
        assert key in body


def step_metrics_and_errors():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/metrics", timeout=10)
    assert r.status_code == 200
    metrics = r.json()
    assert any(m["count"] > 0 for m in metrics), f"expected real recorded latencies: {metrics}"
    r = admin_session.get(f"{BASE}/api/admin/errors", timeout=10)
    assert r.status_code == 200 and isinstance(r.json(), list)


def step_admin_forbidden_for_regular_user():
    r = session.get(f"{BASE}/api/admin/users", timeout=10)
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def step_admin_as_admin():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/analytics", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["total_runs"] >= 1


STEPS = [
    ("health check", step_health),
    ("wait for both local models to finish warming up", step_wait_for_warm),
    ("signup issues a session", step_signup),
    ("auth/me via session cookie", step_me),
    ("CSRF protection blocks a mutating request with no header", step_csrf_blocks_missing_header),
    ("agent: a safe tool run reaches the numerically-correct answer", step_safe_tool_run),
    ("agent: quoted string-argument regression (real bug)", step_quoted_argument_regression),
    ("guardrails: check-order regression (common bug pattern)", step_guardrail_order_regression),
    ("guardrails: amount-aware HITL threshold regression", step_amount_aware_hitl_regression),
    ("agent: stale/abandoned-run reaper regression", step_stale_run_reaper_regression),
    ("HITL: a gated payout pauses the run, admin approves, run resumes", step_hitl_approve_flow),
    ("HITL: a gated payout pauses the run, admin denies, run resumes", step_hitl_deny_flow),
    ("guardrails: step limit stops a multi-step run", step_guardrail_step_limit),
    ("guardrails: cost cap stops a run", step_guardrail_cost_cap),
    ("history: semantic search finds the completed run", step_history_search),
    ("cost governance: $0 budget blocks the escalation call", step_budget_blocks_zero),
    ("model routing: real OpenRouter escalation call", step_openrouter_real_call),
    ("admin: audit log has entries and its hash chain is intact", step_admin_audit_and_integrity),
    ("audit log: tamper detection regression", step_audit_tamper_detection_regression),
    ("rate limiting: the limiter itself actually rejects over-limit calls", step_rate_limit_regression),
    ("account lockout: 5 failed logins lock the account", step_account_lockout),
    ("refresh token rotation: old token rejected after rotation", step_refresh_rotation),
    ("status page: public, no auth required", step_status_page_public),
    ("admin: real metrics + error log endpoints", step_metrics_and_errors),
    ("admin: a regular user is correctly forbidden", step_admin_forbidden_for_regular_user),
    ("admin: the admin account can read analytics", step_admin_as_admin),
]


def main():
    print(f"=== Threshold end-to-end verification ({BASE}) ===\n")
    for name, fn in STEPS:
        print(f"  running: {name} ...")
        check(name, fn)
    print()
    all_ok = True
    for name, ok, elapsed, err in results:
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {name} ({elapsed:.1f}s)"
        if not ok:
            line += f" — {err}"
            all_ok = False
        print(line)
    print()
    if all_ok:
        print("✅ All checks passed.")
        sys.exit(0)
    else:
        print("❌ Some checks failed — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
