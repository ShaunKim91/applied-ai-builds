"""End-to-end smoke test for Verity.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming the streamed research response as
a real client would. Also exercises the new commercial-grade features
(rate limiting, account lockout, refresh-token rotation, CSRF protection,
hash-chained audit-log tamper detection) via direct in-process regression
checks where an isolated, deterministic unit test is more reliable than a
timing-sensitive HTTP round-trip (see each step's own comment for why).

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
results: list[tuple[str, bool, float, str]] = []
_ctx: dict = {}


def check(name: str, fn) -> None:
    start = time.perf_counter()
    try:
        fn()
        results.append((name, True, time.perf_counter() - start, ""))
    except Exception as exc:  # noqa: BLE001 — every failure must be captured, not raised
        results.append((name, False, time.perf_counter() - start, str(exc)))


def csrf_headers() -> dict:
    token = session.cookies.get("csrf_token")
    return {"X-CSRF-Token": token} if token else {}


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
    """A mutating request with the session cookie present but NO
    X-CSRF-Token header must be rejected — proves the double-submit check
    is actually wired in, not just present in code."""
    r = requests.post(
        f"{BASE}/api/research/sessions",
        json={"title": "should be blocked"},
        cookies=session.cookies.get_dict(),
        timeout=10,
    )
    assert r.status_code == 403, f"expected 403 without CSRF header, got {r.status_code}"


def step_research_quick():
    r = session.post(
        f"{BASE}/api/research/sessions",
        json={"title": "Prompt-payment question", "claim_number": "CLM-1001", "jurisdiction": "Cedermoor"},
        headers=csrf_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["id"]
    _ctx["session_id"] = session_id

    r = session.post(
        f"{BASE}/api/research/query",
        json={
            "query": "How quickly must Fenwick Mutual pay the undisputed portion of a claim in Cedermoor?",
            "mode": "quick",
            "jurisdiction": "Cedermoor",
            "claim_number": "CLM-1001",
            "session_id": session_id,
        },
        headers=csrf_headers(),
        timeout=120,
        stream=True,
    )
    assert r.status_code == 200, r.text
    final = None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: ") :])
        if event.get("done"):
            final = event["entry"]
    assert final is not None, "stream never produced a 'done' event"
    assert "15 days" in final["report_text"] or "Cedermoor" in final["report_text"], f"answer didn't engage with the grounded source: {final['report_text'][:200]}"
    assert final["sources"], "no sources were retrieved"
    _ctx["quick_entry"] = final


def step_precedent_brief():
    r = session.post(
        f"{BASE}/api/research/query",
        json={
            "query": "Summarize the filing-deadline rules relevant to claim CLM-1001 in Cedermoor.",
            "mode": "precedent_brief",
            "jurisdiction": "Cedermoor",
            "claim_number": "CLM-1001",
            "session_id": _ctx["session_id"],
        },
        headers=csrf_headers(),
        timeout=120,
        stream=True,
    )
    assert r.status_code == 200, r.text
    final = None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: ") :])
        if event.get("done"):
            final = event["entry"]
    assert final is not None
    assert final["mode"] == "precedent_brief"
    brief = final["brief"]
    assert any(brief.get(k) for k in ("issue", "governing_authority", "facts_applied", "recommendation")), f"precedent brief parsed to nothing: {final['report_text'][:300]}"


def step_ghost_citation_regression():
    """Direct unit check (not HTTP) — the same 'exercise the actual
    production function in-process' technique used across this
    project series' prior PoCs' regression tests. A fabricated URL not among
    the real sources must be flagged."""
    from app.ml import ghost_citation

    real_sources = ["https://statutes.fenwick-demo.example/cedermoor/ins-3814-12"]
    answer = "Payment is due within 15 days [1]. See also https://totally-fabricated.example/fake-citation for more."
    result = ghost_citation.check(answer, real_sources)
    assert result["passed"] is False, "a fabricated URL should have been flagged as a ghost citation"
    assert "https://totally-fabricated.example/fake-citation" in result["ghost_urls"]


def step_fraud_signal_regression():
    from app.ml import fraud_signals

    hits = fraud_signals.check("This looks like a staged low-speed collision with a shared witness across three claimants.")
    assert any(h["id"] == "staged-collision" for h in hits), f"expected a staged-collision signal, got {hits}"

    # Regression for a real, measured false-positive: an embedding-
    # similarity fallback this module used to have flagged EVERY fraud
    # pattern (0.79-0.82 cosine similarity) for a totally unrelated
    # question — removed in favor of keyword-only matching. Confirm a
    # genuinely unrelated question produces zero signals.
    unrelated = fraud_signals.check("How quickly must Fenwick Mutual pay the undisputed portion of a claim in Cedermoor?")
    assert unrelated == [], f"expected no fraud signals for an unrelated question, got {unrelated}"


def step_entity_hallucination_regression():
    """Regression for a real, measured groundedness gap: a Qwen2.5-0.5B
    precedent-brief answer named 'The Federal Insurance Office (FIO)' — a
    real US federal body, invented, appearing in none of the fictional
    Cedermoor sources — and groundedness.verify() scored it a perfect 1.0
    anyway (sentence-similarity tracks topic, not facts). check_entities()
    is the independent, deterministic mitigation."""
    from app.ml import ghost_citation

    sources = ["Cedermoor requires payment of an undisputed portion of a first-party claim within 15 days of acknowledgment of coverage."]
    answer = "Governing Authority: The Federal Insurance Office (FIO) oversees this requirement."
    result = ghost_citation.check_entities(answer, sources)
    assert result["passed"] is False, f"expected the fabricated authority name to be flagged: {result}"
    assert "The Federal Insurance Office" in result["unverified_entities"] or "Federal Insurance Office" in " ".join(result["unverified_entities"])


def step_source_trust_regression():
    from app import pipeline

    assert pipeline.classify_source_trust({"href": "https://statutes.fenwick-demo.example/x"}) == "primary"
    assert pipeline.classify_source_trust({"href": "https://catreports.fenwick-demo.example/x"}) == "secondary"
    assert pipeline.classify_source_trust({"href": "https://example.org/some-blog-post"}) == "unverified"


def step_cat_event():
    r = session.post(
        f"{BASE}/api/cat-events",
        json={"name": "E2E Test Hailstorm", "event_type": "hail", "region": "Cedermoor", "occurred_on": "2025-03-14", "description": "test event"},
        headers=csrf_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text
    event_id = r.json()["id"]
    r = session.get(f"{BASE}/api/cat-events", timeout=10)
    assert r.status_code == 200 and any(e["id"] == event_id for e in r.json())


def step_archive_search():
    r = session.post(f"{BASE}/api/archive/search", json={"query": "prompt payment deadline Cedermoor"}, headers=csrf_headers(), timeout=30)
    assert r.status_code == 200, r.text
    matches = r.json()
    assert any(m["id"] == _ctx["quick_entry"]["id"] for m in matches), f"expected to find the just-created entry via semantic search, got {matches}"


def step_radar_evaluate():
    r = session.post(f"{BASE}/api/radar/evaluate", json={"topic": "an AI claims-triage vendor tool"}, headers=csrf_headers(), timeout=90)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["radar"] is not None or body["extraction_failed"], "radar evaluation returned neither a verdict nor an honest extraction-failed flag"


def step_budget_blocks_zero():
    admin_session, admin_headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 0}, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(
        f"{BASE}/api/research/query",
        json={"query": "test question", "mode": "quick", "use_openrouter": True},
        headers=csrf_headers(),
        timeout=30,
        stream=True,
    )
    body_text = r.text
    assert "budget cap" in body_text.lower(), f"expected a budget-cap message in the stream, got: {body_text[:300]}"

    admin_session2, admin_headers2 = _admin_session()
    r = admin_session2.put(f"{BASE}/api/admin/budget", json={"daily_limit_usd": 1.0}, headers=admin_headers2, timeout=10)
    assert r.status_code == 200


def step_openrouter_real_call():
    r = session.post(
        f"{BASE}/api/research/query",
        json={
            "query": "What is the filing deadline rule in Belmont Bay?",
            "mode": "quick",
            "jurisdiction": "Belmont Bay",
            "use_openrouter": True,
        },
        headers=csrf_headers(),
        timeout=60,
        stream=True,
    )
    assert r.status_code == 200, r.text
    final = None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: ") :])
        if event.get("done"):
            final = event["entry"]
    assert final is not None and final["synth_mode"] == "openrouter", f"expected an openrouter-synthesized entry: {final}"


def _admin_session():
    admin_session = requests.Session()
    r = admin_session.post(f"{BASE}/api/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "admin@fenwickmutual.example"), "password": os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")}, timeout=15)
    assert r.status_code == 200, r.text
    return admin_session, {"X-CSRF-Token": admin_session.cookies.get("csrf_token")}


def step_admin_audit_and_integrity():
    admin_session, headers = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/audit-log", timeout=10)
    assert r.status_code == 200 and len(r.json()) > 0, "expected at least one audit log entry by now"
    r = admin_session.get(f"{BASE}/api/admin/audit-log/verify", timeout=10)
    assert r.status_code == 200 and r.json()["intact"] is True, f"expected an intact hash chain: {r.json()}"


def step_audit_tamper_detection_regression():
    """Directly corrupts one AuditLog row's content (bypassing log_action())
    and confirms verify_chain() correctly reports the break — proof the
    hash chain actually catches tampering, not just that it trivially
    reports 'intact' on an untouched table."""
    from app.database import SessionLocal
    from app.models import AuditLog
    from app.audit import verify_chain

    db = SessionLocal()
    try:
        row = db.query(AuditLog).order_by(AuditLog.id.asc()).first()
        assert row is not None, "expected at least one audit log row to tamper with"
        original_detail = row.detail
        db.query(AuditLog).filter(AuditLog.id == row.id).update({"detail": original_detail + " <tampered>"})
        db.commit()
        result = verify_chain(db)
        assert result["intact"] is False, "expected the hash chain to detect the tampered row"
        assert result["first_broken_id"] == row.id
        # restore, so the rest of the suite (and a human reading the real
        # audit log afterward) sees a genuinely intact chain again.
        db.query(AuditLog).filter(AuditLog.id == row.id).update({"detail": original_detail})
        db.commit()
        result2 = verify_chain(db)
        assert result2["intact"] is True, "expected the chain to be intact again after restoring the row"
    finally:
        db.close()


def step_rate_limit_regression():
    """Direct unit check against a throwaway bucket key — isolated from the
    real HTTP-driven 'auth'/'ai' buckets so this test's own volume of calls
    can't interfere with (or be interfered with by) the login/lockout test
    below, which shares the real 'auth' bucket over actual HTTP."""
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
    assert r.status_code == 423, f"expected the account to be locked (423) even with the correct password, got {r.status_code}"


def step_refresh_rotation():
    login_session = requests.Session()
    r = login_session.post(f"{BASE}/api/auth/login", json={"email": _ctx["email"], "password": "TestPass123!"}, timeout=15)
    assert r.status_code == 200, r.text
    old_refresh = login_session.cookies.get("refresh_token")

    r = login_session.post(f"{BASE}/api/auth/refresh", timeout=10)
    assert r.status_code == 200, r.text
    new_refresh = login_session.cookies.get("refresh_token")
    assert new_refresh != old_refresh, "refresh token should rotate to a new value"

    # Reusing the OLD refresh token must now fail — it was revoked on rotation.
    stale_session = requests.Session()
    stale_session.cookies.set("refresh_token", old_refresh)
    r = stale_session.post(f"{BASE}/api/auth/refresh", timeout=10)
    assert r.status_code == 401, f"expected a revoked/reused refresh token to be rejected, got {r.status_code}"


def step_status_page_public():
    r = requests.get(f"{BASE}/api/status", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("app", "uptime_seconds", "models_warm", "vector_store_reachable", "openrouter_configured"):
        assert key in body, f"missing expected status field: {key}"


def step_metrics_and_errors():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/metrics", timeout=10)
    assert r.status_code == 200
    metrics = r.json()
    assert any(m["count"] > 0 for m in metrics), f"expected at least one route with real recorded latencies: {metrics}"
    r = admin_session.get(f"{BASE}/api/admin/errors", timeout=10)
    assert r.status_code == 200 and isinstance(r.json(), list)


def step_admin_forbidden_for_regular_user():
    r = session.get(f"{BASE}/api/admin/users", timeout=10)
    assert r.status_code == 403, f"expected a regular user to be forbidden from admin routes, got {r.status_code}"


def step_admin_as_admin():
    admin_session, _ = _admin_session()
    r = admin_session.get(f"{BASE}/api/admin/analytics", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["total_reports"] >= 1


STEPS = [
    ("health check", step_health),
    ("wait for both local models to finish warming up", step_wait_for_warm),
    ("signup issues a session", step_signup),
    ("auth/me via session cookie", step_me),
    ("CSRF protection blocks a mutating request with no header", step_csrf_blocks_missing_header),
    ("research: quick-mode query grounded in the fictional Cedermoor corpus", step_research_quick),
    ("research: precedent-brief mode produces structured sections", step_precedent_brief),
    ("ghost-citation regression: a fabricated URL is flagged", step_ghost_citation_regression),
    ("fraud-signal regression: keyword match fires, unrelated text doesn't", step_fraud_signal_regression),
    ("groundedness gap regression: a hallucinated real-world authority is flagged", step_entity_hallucination_regression),
    ("source-trust regression: tier classification is correct", step_source_trust_regression),
    ("CAT events: create + list", step_cat_event),
    ("archive: semantic search finds the just-created entry", step_archive_search),
    ("radar: real OpenRouter-free vendor evaluation (real live web search)", step_radar_evaluate),
    ("cost governance: $0 budget blocks the OpenRouter path", step_budget_blocks_zero),
    ("model routing: real OpenRouter call", step_openrouter_real_call),
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
    print(f"=== Verity end-to-end verification ({BASE}) ===\n")
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
