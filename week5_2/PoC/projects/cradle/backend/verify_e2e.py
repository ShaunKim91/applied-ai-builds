"""End-to-end smoke test for Cradle.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming the streamed agent-run response as
a real client would, and actually running a paused-for-approval run through
to resumption. Matches the verification discipline of the Week1-14_1 PoCs.

Run from inside the container (has network access + all deps installed):
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
token = {"value": None}
results: list[tuple[str, bool, float, str]] = []
_ctx: dict = {}


def check(name: str, fn) -> None:
    start = time.perf_counter()
    try:
        fn()
        results.append((name, True, time.perf_counter() - start, ""))
    except Exception as exc:  # noqa: BLE001 — every failure must be captured, not raised
        results.append((name, False, time.perf_counter() - start, str(exc)))


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {token['value']}"} if token["value"] else {}


def _admin_session():
    admin_session = requests.Session()
    r = admin_session.post(
        f"{BASE}/api/auth/login",
        json={
            "email": os.environ.get("ADMIN_EMAIL", "admin@cradle.local"),
            "password": os.environ.get("ADMIN_PASSWORD", "ChangeMe123!"),
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return admin_session, {"Authorization": f"Bearer {r.json()['access_token']}"}


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
        step_errors = body.get("bootstrap_step_errors", {})
        model_errors = {k: v for k, v in step_errors.items() if k.startswith("model:")}
        if body.get("bootstrap_complete") and model_errors and not body.get("all_warm"):
            raise AssertionError(f"a model failed to warm up: {model_errors}")
        if time.time() - last_print > 15:
            not_yet = [k for k, v in body.get("models", {}).items() if not v]
            print(f"    ... still warming up: {', '.join(not_yet) or 'unknown'}")
            last_print = time.time()
        time.sleep(3)
    raise AssertionError("models did not finish warming up within 20 minutes")


def step_signup():
    email = f"e2e-{int(time.time())}@example.com"
    r = session.post(
        f"{BASE}/api/auth/signup",
        json={"email": email, "password": "TestPass123!", "display_name": "E2E Bot"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    token["value"] = r.json()["access_token"]
    _ctx["e2e_email"] = email


def step_me():
    r = session.get(f"{BASE}/api/auth/me", headers=auth_headers(), timeout=10)
    assert r.status_code == 200


def _stream_run(question: str, timeout: int = 90) -> dict:
    with session.post(
        f"{BASE}/api/agent/runs",
        headers=auth_headers(),
        json={"question": question},
        stream=True,
        timeout=timeout,
    ) as r:
        assert r.status_code == 200, r.text
        final_event = None
        step_events = []
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: ") :])
            if event.get("step_complete"):
                step_events.append(event)
            if event.get("done"):
                final_event = event
        assert final_event is not None, "stream ended without a final 'done' event"
        return {"final": final_event, "steps": step_events}


def step_agent_calculator_run():
    """A real tool-use run: the agent must call calculator and arrive at
    the numerically-correct answer, not just call a tool at all — a known
    real failure mode for small local models, where the tool call was
    correct but the model's OWN final-answer summarization step still
    fabricated a different number."""
    result = _stream_run("What is 127 * 39? Use the calculator tool.")
    assert result["final"]["status"] == "COMPLETED", result["final"]
    answer = result["final"]["final_answer"]
    assert "4953" in answer, f"expected the correct product 4953 somewhere in the answer, got: {answer!r}"
    _ctx["calc_run_ok"] = True


def step_guardrail_order_regression():
    """Direct unit check of agent/guardrails.py's check order — guards
    against a naive ordering where cost-cap is checked BEFORE permission,
    which would mislabel an unauthorized-tool call made after the budget
    was already exhausted as STOPPED_COST_CAP instead of
    BLOCKED_PERMISSION. Reproduces exactly that scenario."""
    from app.agent.guardrails import check_guardrails

    verdict = check_guardrails(
        "delete_customer_data",
        step_count=3,
        max_steps=5,
        allowed_tools={"calculator", "lookup_faq"},
        tool_cost={"calculator": 5, "lookup_faq": 10},
        spent=15,  # already at/over a cost_cap of 15 in this scenario
        cost_cap=15,
        hitl_tools=set(),
    )
    assert verdict.status == "BLOCKED_PERMISSION", (
        f"expected BLOCKED_PERMISSION (permission checked before cost cap), got {verdict.status} — "
        f"this is the exact ordering bug a naive implementation of this pattern would produce"
    )


def step_stale_run_reaper_regression():
    """Regression check for debug/issue-03: a run whose SSE stream was
    abandoned mid-flight (client disconnect) used to stay 'RUNNING' forever
    — nothing else could ever advance it. Rather than waiting out the real
    180s staleness window in this test, manufacture an already-stale
    'RUNNING' row directly (same technique as the guardrail-order check:
    exercise the actual production function in-process) and confirm the
    lazy reaper in routers/agent.py correctly resolves it to FAILED, with
    an honest explanation, the next time runs are listed."""
    import datetime as dt

    from app.database import SessionLocal
    from app.models import AgentRun, User
    from app.routers.agent import _reap_stale_runs

    db = SessionLocal()
    try:
        # Deliberately the throwaway e2e-bot account from step_signup(), NOT
        # db.query(User).first() — that used to grab whichever row has the
        # lowest id, which is always the seeded admin (admin is created
        # before any test user ever signs up). The synthetic "stale run"
        # this test manufactures was landing in the REAL admin account's own
        # Console/Dashboard/History — the exact account used to operate and
        # demo the product — rather than in the disposable test identity the
        # rest of this suite already uses. See debug/issue-05.
        e2e_email = _ctx.get("e2e_email")
        assert e2e_email, "step_signup() must run before this check"
        user = db.query(User).filter(User.email == e2e_email).first()
        assert user is not None, "expected the e2e-bot test user to exist"
        stale = AgentRun(
            owner_id=user.id,
            question="(regression test — simulated abandoned run)",
            status="RUNNING",
            step_count=1,
            messages_json="[]",
        )
        db.add(stale)
        db.commit()
        db.refresh(stale)
        # Backdate updated_at past the staleness window without waiting for
        # real time to pass — this is the one field the reaper actually
        # keys off of.
        db.query(AgentRun).filter(AgentRun.id == stale.id).update(
            {"updated_at": dt.datetime.utcnow() - dt.timedelta(seconds=181)}
        )
        db.commit()

        _reap_stale_runs(db, user.id)

        db.refresh(stale)
        assert stale.status == "FAILED", f"expected the stale run to be reaped to FAILED, got {stale.status!r}"
        assert stale.final_answer, "expected an honest explanation, not a blank final_answer"
    finally:
        db.close()


def step_hitl_flow():
    """The real, actually-wired Human-in-the-Loop loop that a typical
    baseline implementation never connects to its own shipped app: trigger
    a HITL-gated tool call, confirm the run pauses with a real pending
    approval request, have the admin approve it, and confirm the run
    actually resumes and completes."""
    result = _stream_run("Use the issue_refund tool for order ORD-9001.")
    assert result["final"]["status"] == "AWAITING_APPROVAL", (
        f"expected the run to pause for approval, got: {result['final']}"
    )
    approval_id = result["final"]["approval_request_id"]
    _ctx["approval_id"] = approval_id

    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/approvals?status=pending", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    pending_ids = [a["id"] for a in r.json()]
    assert approval_id in pending_ids, f"approval {approval_id} not found in the pending queue: {pending_ids}"

    r = admin_session.post(
        f"{BASE}/api/approvals/{approval_id}/decide",
        headers=headers,
        json={"approve": True, "reason": "E2E test approval"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["approval"]["status"] == "approved"
    assert body["run_result"] is not None and body["run_result"]["status"] == "COMPLETED", body["run_result"]


def step_hitl_denial_flow():
    """The denial path — the run must still resume (not crash) and reach a
    terminal state after a reviewer denies the gated action."""
    result = _stream_run("Use the issue_refund tool for order ORD-9002.")
    assert result["final"]["status"] == "AWAITING_APPROVAL", result["final"]
    approval_id = result["final"]["approval_request_id"]

    admin_session, headers = _admin_session()
    r = admin_session.post(
        f"{BASE}/api/approvals/{approval_id}/decide",
        headers=headers,
        json={"approve": False, "reason": "E2E test denial"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    assert r.json()["approval"]["status"] == "denied"
    assert r.json()["run_result"] is not None


def step_step_limit():
    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/guardrails", headers=headers, timeout=15)
    original = r.json()
    r = admin_session.put(
        f"{BASE}/api/admin/guardrails",
        headers=headers,
        json={"allowed_tools": original["allowed_tools"], "max_steps": 1, "cost_cap": original["cost_cap"]},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    try:
        result = _stream_run("First look up the refund FAQ, then look up the shipping FAQ, then give me both.")
        assert result["final"]["status"] == "STOPPED_STEP_LIMIT", result["final"]
    finally:
        admin_session.put(
            f"{BASE}/api/admin/guardrails",
            headers=headers,
            json={"allowed_tools": original["allowed_tools"], "max_steps": original["max_steps"], "cost_cap": original["cost_cap"]},
            timeout=15,
        )


def step_cost_cap():
    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/guardrails", headers=headers, timeout=15)
    original = r.json()
    r = admin_session.put(
        f"{BASE}/api/admin/guardrails",
        headers=headers,
        json={"allowed_tools": original["allowed_tools"], "max_steps": original["max_steps"], "cost_cap": 1},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    try:
        result = _stream_run("What is 5 + 5? Use the calculator tool.")
        assert result["final"]["status"] == "STOPPED_COST_CAP", result["final"]
    finally:
        admin_session.put(
            f"{BASE}/api/admin/guardrails",
            headers=headers,
            json={"allowed_tools": original["allowed_tools"], "max_steps": original["max_steps"], "cost_cap": original["cost_cap"]},
            timeout=15,
        )


def step_history_search():
    if not _ctx.get("calc_run_ok"):
        raise AssertionError("prerequisite calculator run did not complete")
    r = session.post(f"{BASE}/api/history/search", headers=auth_headers(), json={"query": "127 times 39", "top_k": 5}, timeout=20)
    assert r.status_code == 200, r.text
    assert len(r.json()) > 0, "expected the completed calculator run to be findable via semantic search"


def step_budget_governance_blocks_escalation():
    admin_session, headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/budget", headers=headers, json={"daily_limit_usd": 0.0}, timeout=10)
    assert r.status_code == 200, r.text

    # Force a run into STOPPED_STEP_LIMIT so escalation is offered at all.
    r = admin_session.get(f"{BASE}/api/admin/guardrails", headers=headers, timeout=15)
    original = r.json()
    admin_session.put(
        f"{BASE}/api/admin/guardrails",
        headers=headers,
        json={"allowed_tools": original["allowed_tools"], "max_steps": 1, "cost_cap": original["cost_cap"]},
        timeout=15,
    )
    try:
        result = _stream_run("Look up two different FAQ entries and summarize both.")
        run_id = result["final"]["run_id"]
        r3 = session.post(f"{BASE}/api/agent/runs/{run_id}/escalate", headers=auth_headers(), timeout=30)
        assert r3.status_code == 402, f"expected a 402 budget-cap rejection, got {r3.status_code}: {r3.text}"
    finally:
        admin_session.put(
            f"{BASE}/api/admin/guardrails",
            headers=headers,
            json={"allowed_tools": original["allowed_tools"], "max_steps": original["max_steps"], "cost_cap": original["cost_cap"]},
            timeout=15,
        )
        admin_session.put(f"{BASE}/api/admin/budget", headers=headers, json={"daily_limit_usd": 1.00}, timeout=10)


def step_real_escalation_call():
    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/guardrails", headers=headers, timeout=15)
    original = r.json()
    admin_session.put(
        f"{BASE}/api/admin/guardrails",
        headers=headers,
        json={"allowed_tools": original["allowed_tools"], "max_steps": 1, "cost_cap": original["cost_cap"]},
        timeout=15,
    )
    try:
        result = _stream_run("Look up two different FAQ entries and summarize both.")
        run_id = result["final"]["run_id"]
        r3 = session.post(f"{BASE}/api/agent/runs/{run_id}/escalate", headers=auth_headers(), timeout=30)
        assert r3.status_code == 200, r3.text
        assert r3.json()["final_answer"], "escalation produced no answer text"
    finally:
        admin_session.put(
            f"{BASE}/api/admin/guardrails",
            headers=headers,
            json={"allowed_tools": original["allowed_tools"], "max_steps": original["max_steps"], "cost_cap": original["cost_cap"]},
            timeout=15,
        )


def step_admin_rejected_for_regular_user():
    r = session.get(f"{BASE}/api/admin/analytics", headers=auth_headers(), timeout=10)
    assert r.status_code == 403, "a regular user must NOT be able to read admin endpoints"


def step_admin_as_admin():
    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/system", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert "models" in r.json() and "counts" in r.json()
    r = admin_session.get(f"{BASE}/api/admin/analytics", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["run_count"] >= 3


STEPS = [
    ("health check", step_health),
    ("wait for both local models to finish warming up", step_wait_for_warm),
    ("signup issues a JWT", step_signup),
    ("auth/me via Bearer token", step_me),
    ("agent: a calculator run reaches the numerically-correct answer", step_agent_calculator_run),
    ("guardrails: check-order regression (naive-order bug)", step_guardrail_order_regression),
    ("agent: stale/abandoned-run reaper regression", step_stale_run_reaper_regression),
    ("HITL: a gated tool pauses the run, admin approves, run resumes", step_hitl_flow),
    ("HITL: a gated tool pauses the run, admin denies, run resumes", step_hitl_denial_flow),
    ("guardrails: step limit stops a multi-step run", step_step_limit),
    ("guardrails: cost cap stops a run", step_cost_cap),
    ("history: semantic search finds the completed run", step_history_search),
    ("cost governance: $0 budget blocks the escalation call", step_budget_governance_blocks_escalation),
    ("model routing: real OpenRouter escalation call", step_real_escalation_call),
    ("admin: a regular user is correctly forbidden", step_admin_rejected_for_regular_user),
    ("admin: the admin account can read system status + analytics", step_admin_as_admin),
]

print(f"=== Cradle end-to-end verification ({BASE}) ===\n")
for name, fn in STEPS:
    print(f"  running: {name} ...")
    check(name, fn)

print()
all_ok = True
for name, passed, dur, err in results:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {name} ({dur:.1f}s)"
    if err:
        line += f" — {err}"
    print(line)
    all_ok = all_ok and passed

print()
if all_ok:
    print("✅ All checks passed.")
    sys.exit(0)
print("❌ Some checks failed — see above.")
sys.exit(1)
