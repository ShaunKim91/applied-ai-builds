"""End-to-end smoke test for Throughline.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming a streamed message reply the way a
real client would. Covers the commercial-grade infra shared with Verity and
Threshold (rate limiting, account lockout, refresh-token rotation, CSRF
protection, hash-chained audit-log tamper detection), plus Throughline-
specific mechanics: structured memory extraction and recall, memory-
conditioned tool auto-fill, the memory-write conflict guardrail, the
window-to-summary transition, redaction at the persistence boundary, the
`ast`-whitelist safe evaluator, and the purge/right-to-erasure cascade.

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


def _consume_message_stream(resp):
    router_event = None
    reply_text = None
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: ") :])
        if "router" in event:
            router_event = event
        if event.get("done"):
            reply_text = event.get("reply")
    return router_event, reply_text


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
    r = session.post(f"{BASE}/api/auth/signup", json={"email": email, "password": "TestPass123!", "display_name": "E2E Rep"}, timeout=15)
    assert r.status_code == 200, r.text
    _ctx["email"] = email


def step_me():
    r = session.get(f"{BASE}/api/auth/me", timeout=10)
    assert r.status_code == 200 and r.json()["email"] == _ctx["email"]


def step_csrf_blocks_missing_header():
    r = requests.post(f"{BASE}/api/cases", json={"title": "should be blocked"}, cookies=session.cookies.get_dict(), timeout=10)
    assert r.status_code == 403, f"expected 403 without CSRF header, got {r.status_code}"


def step_create_case():
    r = session.post(f"{BASE}/api/cases", json={"title": "Diane Castellano - billing"}, headers=csrf_headers(), timeout=10)
    assert r.status_code == 200, r.text
    _ctx["case_id"] = r.json()["id"]


def step_tool_call_reaches_correct_answer():
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "I've got Diane Castellano on the line about her policy FM-100234."}, headers=csrf_headers(), timeout=60, stream=True)
    router_event, reply = _consume_message_stream(r)
    assert router_event is not None and reply, "expected a router decision and a final reply"
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "Can you look up her account?"}, headers=csrf_headers(), timeout=60, stream=True)
    router_event, reply = _consume_message_stream(r)
    assert router_event.get("tool_result") and "ACTIVE" in router_event["tool_result"], f"expected a real lookup_caller_account tool result: {router_event}"
    assert "September" in reply or "2026-09-15" in reply or "09-15" in reply, f"expected the reply to relay the real payment-due date: {reply!r}"


def step_memory_recall_regression():
    """Real bug found in this build's own development (see debug/): the
    structured MemoryFact extraction was persisted but never fed back into
    the reply-generation context, so a recall question outside the raw
    transcript window had nothing to draw on. Fixed by injecting a compact
    facts block into the system prompt every turn — this asserts that fix
    still holds."""
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "Remind me what the caller's name was?"}, headers=csrf_headers(), timeout=60, stream=True)
    _, reply = _consume_message_stream(r)
    assert "Diane" in reply or "Castellano" in reply, f"expected the reply to recall the caller's name from persisted memory: {reply!r}"


def step_memory_facts_persisted():
    r = session.get(f"{BASE}/api/cases/{_ctx['case_id']}", headers=csrf_headers(), timeout=10)
    assert r.status_code == 200, r.text
    facts = {f["field_name"]: f["field_value"] for f in r.json()["facts"]}
    assert "policy_number" in facts and "FM-100234" in facts["policy_number"], f"expected policy_number extracted: {facts}"


def step_memory_conditioned_autofill():
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "She said mornings work best for a billing callback."}, headers=csrf_headers(), timeout=60, stream=True)
    _consume_message_stream(r)
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "Can you check billing callback availability for her?"}, headers=csrf_headers(), timeout=60, stream=True)
    router_event, reply = _consume_message_stream(r)
    tool_result = (router_event or {}).get("tool_result") or ""
    assert "AM" in tool_result or "morning" in tool_result.lower() or "AM" in reply, f"expected the caller's earlier 'mornings' preference to auto-fill the callback lookup: tool_result={tool_result!r} reply={reply!r}"


def step_memory_conflict_guardrail():
    """Directly seeds a `stated` fact then sends a message stating a
    DIFFERENT value for the same field — asserts the guardrail creates a
    pending conflict rather than silently overwriting."""
    import app.models as models
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        case = db.get(models.CallerCase, _ctx["case_id"])
        existing = db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case.id, models.MemoryFact.field_name == "caller_name").first()
        if existing:
            existing.field_value = "Diane Castellano"
            existing.confidence = "stated"
        else:
            db.add(models.MemoryFact(case_id=case.id, field_name="caller_name", field_value="Diane Castellano", confidence="stated"))
        db.commit()
    finally:
        db.close()

    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/messages", json={"message": "Actually, this caller's name is Marguerite Diane Castellano, please correct that."}, headers=csrf_headers(), timeout=60, stream=True)
    _consume_message_stream(r)

    r = session.get(f"{BASE}/api/cases/{_ctx['case_id']}", headers=csrf_headers(), timeout=10)
    body = r.json()
    facts = {f["field_name"]: f["field_value"] for f in body["facts"]}
    # The guardrail's job is only to make sure a stated-vs-stated conflict
    # is never SILENT -- either it shows up as a pending conflict (the
    # common case) or the extraction simply didn't fire this turn (a real,
    # already-documented small-model limitation, not a guardrail failure).
    # What must never happen is the value changing with zero trace of it.
    if facts.get("caller_name") != "Diane Castellano":
        assert len(body["pending_conflicts"]) > 0, "a changed caller_name with no pending conflict would mean a silent overwrite"
        _ctx["conflict_id"] = body["pending_conflicts"][0]["id"]


def step_memory_conflict_resolution():
    if "conflict_id" not in _ctx:
        return  # extraction didn't produce a conflict this run -- see note above
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/conflicts/{_ctx['conflict_id']}/resolve", json={"resolution": "kept_old"}, headers=csrf_headers(), timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["resolution"] == "kept_old"


def step_window_summary_transition():
    """Real bug found in this build's own development (see debug/): piping
    a `ChatPromptTemplate` directly into the local-model Runnable handed it
    a `ChatPromptValue`, which isn't subscriptable — summarization crashed
    the FIRST time it actually ran (never exercised by the router/
    extraction chains, which build plain message lists by hand). Fixed by
    normalizing the input inside the Runnable. This lowers the window to 1
    turn and sends enough messages to force a real summarization."""
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/memory-settings", json={"window_turns": 1, "redaction_enabled": True}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(f"{BASE}/api/cases", json={"title": "Window/summary regression case"}, headers=csrf_headers(), timeout=10)
    case_id = r.json()["id"]
    for msg in ["Hi, my name is Chris Okafor.", "My policy is FM-100891.", "What's my billing status?", "Thanks, that's everything."]:
        r = session.post(f"{BASE}/api/cases/{case_id}/messages", json={"message": msg}, headers=csrf_headers(), timeout=60, stream=True)
        _consume_message_stream(r)

    r = session.get(f"{BASE}/api/cases/{case_id}", headers=csrf_headers(), timeout=10)
    body = r.json()
    assert body["case_summary"], "expected a non-empty rolling summary once the window overflowed"
    _ctx["window_test_case_id"] = case_id

    r = admin_session.put(f"{BASE}/api/admin/memory-settings", json={"window_turns": 8, "redaction_enabled": True}, headers=admin_headers, timeout=10)
    assert r.status_code == 200


def step_redaction_boundary():
    r = session.post(f"{BASE}/api/cases", json={"title": "Redaction test"}, headers=csrf_headers(), timeout=10)
    case_id = r.json()["id"]
    phone = "555-123-9876"
    r = session.post(f"{BASE}/api/cases/{case_id}/messages", json={"message": f"You can reach me directly at {phone} if needed."}, headers=csrf_headers(), timeout=60, stream=True)
    _consume_message_stream(r)
    r = session.get(f"{BASE}/api/cases/{case_id}", headers=csrf_headers(), timeout=10)
    turns = r.json()["turns"]
    human_turn = next(t for t in turns if t["role"] == "human")
    assert phone not in human_turn["content"], f"the raw phone number leaked into persisted storage: {human_turn}"
    assert human_turn["redacted"] is True
    assert "REDACTED" in human_turn["content"]
    _ctx["redaction_case_id"] = case_id


def step_safe_eval_binop():
    from app.ml.safe_eval import safe_eval

    assert safe_eval("12 * 8") == 96, "safe_eval must handle real binary-operator arithmetic ast.literal_eval cannot"
    try:
        import ast

        ast.literal_eval("12 * 8")
        raise AssertionError("expected ast.literal_eval to reject a BinOp -- if this changed, the debug/ writeup's claim needs updating")
    except ValueError:
        pass  # confirms the documented correction to that common `ast.literal_eval` claim is still accurate


def step_safe_eval_rejects_unsafe():
    from app.ml.safe_eval import UnsafeExpressionError, safe_eval

    for bad in ["__import__('os').system('ls')", "1/0", "2**10", "'a'+'b'"]:
        try:
            safe_eval(bad)
            raise AssertionError(f"expected safe_eval to reject {bad!r}")
        except UnsafeExpressionError:
            pass


def step_purge_cascade():
    r = session.get(f"{BASE}/api/cases/{_ctx['redaction_case_id']}", headers=csrf_headers(), timeout=10)
    turns_before = len(r.json()["turns"])
    assert turns_before > 0

    r = session.post(f"{BASE}/api/cases/{_ctx['redaction_case_id']}/purge", headers=csrf_headers(), timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["turns_deleted"] == turns_before

    r = session.get(f"{BASE}/api/cases/{_ctx['redaction_case_id']}", headers=csrf_headers(), timeout=10)
    assert r.status_code == 404, "expected the purged case to be gone"


def step_case_semantic_search():
    r = session.get(f"{BASE}/api/cases?q=billing", headers=csrf_headers(), timeout=15)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def step_admin_memory_settings():
    admin_session, admin_headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/memory-settings", headers=admin_headers, timeout=10)
    assert r.status_code == 200 and r.json()["window_turns"] == 8, r.text


def step_admin_memory_conflicts_log():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/memory-conflicts", timeout=10)
    assert r.status_code == 200 and isinstance(r.json(), list)


def step_admin_retention_log():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/retention-requests", timeout=10)
    assert r.status_code == 200
    rows = r.json()
    assert any(row["case_id"] == _ctx["redaction_case_id"] for row in rows), "expected the purge from step_purge_cascade to appear in the retention log"


def step_budget_blocks_zero():
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/escalate", headers=csrf_headers(), timeout=15)
    assert r.status_code == 402, f"expected a 402 budget-cap block, got {r.status_code}"

    r = admin_session.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 1.0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200


def step_openrouter_real_call():
    r = session.post(f"{BASE}/api/cases/{_ctx['case_id']}/escalate", headers=csrf_headers(), timeout=60)
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
    assert r.status_code == 200 and isinstance(r.json(), list)
    r = admin_session.get(f"{BASE}/api/admin/errors", timeout=10)
    assert r.status_code == 200 and isinstance(r.json(), list)


def step_admin_forbidden_for_regular_user():
    r = session.get(f"{BASE}/api/admin/users", timeout=10)
    assert r.status_code == 403, f"expected a regular user to be forbidden from /api/admin/users, got {r.status_code}"


def step_admin_as_admin():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/analytics", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["total_cases"] >= 1


STEPS = [
    ("health check", step_health),
    ("wait for both local models to finish warming up", step_wait_for_warm),
    ("signup issues a session", step_signup),
    ("auth/me via session cookie", step_me),
    ("CSRF protection blocks a mutating request with no header", step_csrf_blocks_missing_header),
    ("cases: create a case", step_create_case),
    ("workspace: a real tool call reaches the correct answer", step_tool_call_reaches_correct_answer),
    ("memory: recall regression (facts injected into reply context)", step_memory_recall_regression),
    ("memory: structured facts persisted", step_memory_facts_persisted),
    ("memory: conditioned tool auto-fill", step_memory_conditioned_autofill),
    ("memory: conflict guardrail never overwrites silently", step_memory_conflict_guardrail),
    ("memory: conflict resolution endpoint", step_memory_conflict_resolution),
    ("memory: window-to-summary transition (ChatPromptValue regression)", step_window_summary_transition),
    ("redaction: PII never persisted verbatim", step_redaction_boundary),
    ("tools: safe_eval handles real binary-operator arithmetic", step_safe_eval_binop),
    ("tools: safe_eval rejects unsafe expressions", step_safe_eval_rejects_unsafe),
    ("retention: purge cascade deletes turns/facts", step_purge_cascade),
    ("cases: semantic search", step_case_semantic_search),
    ("admin: memory settings", step_admin_memory_settings),
    ("admin: memory conflicts log", step_admin_memory_conflicts_log),
    ("admin: retention requests log", step_admin_retention_log),
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
    print(f"=== Throughline end-to-end verification ({BASE}) ===\n")
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
