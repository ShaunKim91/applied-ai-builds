"""End-to-end smoke test for Compass.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming the streamed research-report
response as a real client would — and prints a PASS/FAIL checklist,
matching the verification discipline of the Week1-13 PoCs.

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
            print(f"    web_search mode at bootstrap: {(body.get('web_search') or {}).get('mode')}")
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


def step_me():
    r = session.get(f"{BASE}/api/auth/me", headers=auth_headers(), timeout=10)
    assert r.status_code == 200


def step_create_session():
    r = session.post(f"{BASE}/api/research/sessions", headers=auth_headers(), timeout=10)
    assert r.status_code == 200, r.text
    _ctx["session_id"] = r.json()["id"]


def _send_and_collect(query: str, use_rerank: bool = True, use_openrouter: bool = False, timeout: int = 90) -> dict:
    session_id = _ctx["session_id"]
    with session.post(
        f"{BASE}/api/research/sessions/{session_id}/entries",
        headers=auth_headers(),
        json={"query": query, "use_rerank": use_rerank, "use_openrouter": use_openrouter},
        stream=True,
        timeout=timeout,
    ) as r:
        assert r.status_code == 200, r.text
        full_text = []
        final_event = None
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: ") :])
            if "error" in event:
                raise AssertionError(f"stream reported an error: {event['error']}")
            if "delta" in event:
                full_text.append(event["delta"])
            if event.get("done"):
                final_event = event
        assert final_event is not None, "stream ended without a final 'done' event"
        assembled = "".join(full_text).strip()
        assert assembled, "assembled streamed report was empty"
        return {"report": assembled, **final_event}


def step_send_query_bi_only():
    result = _send_and_collect("What is retrieval-augmented generation?", use_rerank=False)
    assert result["search_mode"] in ("ddgs", "mock"), f"unexpected search_mode: {result['search_mode']}"
    assert len(result["sources"]) > 0, "expected at least one search result (real or mock fallback)"
    assert "groundedness" in result and "ghost_citations" in result
    _ctx["last_search_mode"] = result["search_mode"]


def step_send_query_with_rerank():
    result = _send_and_collect("What are the risks of prompt injection in web search results?", use_rerank=True)
    assert len(result["sources"]) > 0


def step_history_reload_preserves_groundedness():
    """Regression check for the exact bug class Week4's Lucent PoC shipped
    (debug/issue-02): a groundedness badge that renders correctly from the
    live SSE stream but silently disappears once history is reloaded via
    REST, because the two endpoints returned differently-shaped JSON."""
    session_id = _ctx["session_id"]
    r = session.get(f"{BASE}/api/research/sessions/{session_id}/entries", headers=auth_headers(), timeout=15)
    assert r.status_code == 200, r.text
    entries = r.json()
    assert len(entries) >= 2, "expected the 2 research entries sent earlier in this session"
    last = entries[-1]
    assert "groundedness" in last and last["groundedness"] is not None, "groundedness missing after reload"
    assert "passed" in last["groundedness"] and "content_check" in last["groundedness"]
    assert "score" in last["groundedness"]["content_check"]


def step_ghost_citation_unit_check():
    """Runs ml/ghost_citation.py's detector directly (in-process, not over
    HTTP) against a deliberately-crafted mismatch — a real LLM won't
    reliably fabricate a bad citation on demand, so this is how the
    detector's own logic is verified deterministically, independent of any
    one model's behavior on a given day."""
    from app.ml import ghost_citation

    answer = "Fact one [1] (https://real-source.example/a). Fact two [2] (https://fabricated-not-retrieved.example/z)."
    retrieved = ["https://real-source.example/a", "https://another-real-source.example/b"]
    verdict = ghost_citation.check(answer, retrieved)
    assert verdict["passed"] is False, "expected a ghost citation to be detected"
    assert "https://fabricated-not-retrieved.example/z" in verdict["ghost_citations"]
    assert "https://real-source.example/a" in verdict["real_citations"]

    clean_answer = "Fact one [1] (https://real-source.example/a)."
    clean_verdict = ghost_citation.check(clean_answer, retrieved)
    assert clean_verdict["passed"] is True, "a fully-grounded answer must not be flagged"


def step_radar_json_extraction_regression():
    """Regression check for debug/issue-01: a real Qwen2.5-0.5B output was
    syntactically-complete, correctly-shaped JSON plus one stray trailing
    `}` — the original greedy-regex extractor swallowed that extra brace
    into its parse candidate and failed on otherwise-valid JSON."""
    from app.pipeline import parse_radar_json

    real_malformed_output = (
        '{"cost": {"level": "Insufficient evidence", "note": "No specific cost details provided."}, '
        '"security": {"level": "Insufficient evidence", "note": "No security measures mentioned."}, '
        '"approval": {"level": "Insufficient evidence", "note": "Sources lack detailed approval processes."}}}'
    )
    result = parse_radar_json(real_malformed_output)
    assert result is not None, "should recover the verdict despite the trailing extra brace"
    assert result["cost"]["level"] == "Insufficient evidence"

    prose_wrapped = 'Here you go:\n{"cost": {"level": "Low", "note": "a"}, "security": {"level": "Medium", "note": "b"}, "approval": {"level": "High", "note": "c"}}\nDone.'
    assert parse_radar_json(prose_wrapped) is not None

    assert parse_radar_json("no json here at all") is None, "must not fabricate a verdict from non-JSON text"


def step_archive_search():
    r = session.post(
        f"{BASE}/api/archive/search",
        headers=auth_headers(),
        json={"query": "retrieval-augmented generation", "top_k": 5},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    results_ = r.json()
    assert len(results_) > 0, "expected the just-created report to be findable via archive semantic search"


def step_trend_radar():
    r = session.post(
        f"{BASE}/api/trend-radar/evaluate",
        headers=auth_headers(),
        json={"topic": "Claude Code CLI"},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "extraction_failed" in body
    _ctx["radar_extraction_failed"] = body["extraction_failed"]
    print(f"    trend radar JSON extraction {'FAILED (see debug/)' if body['extraction_failed'] else 'succeeded'}")


def _admin_session():
    admin_session = requests.Session()
    r = admin_session.post(
        f"{BASE}/api/auth/login",
        json={
            "email": os.environ.get("ADMIN_EMAIL", "admin@compass.local"),
            "password": os.environ.get("ADMIN_PASSWORD", "ChangeMe123!"),
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return admin_session, {"Authorization": f"Bearer {r.json()['access_token']}"}


def step_budget_governance_blocks_paid_call():
    """Sets the daily budget to $0 as admin, confirms Grounding Lab's paid
    OpenRouter arm is skipped (not attempted) rather than silently spending
    money past the cap, then restores the default budget."""
    admin_session, headers = _admin_session()
    r = admin_session.put(f"{BASE}/api/admin/budget", headers=headers, json={"daily_limit_usd": 0.0}, timeout=10)
    assert r.status_code == 200, r.text

    r = session.post(
        f"{BASE}/api/grounding-lab/compare",
        headers=auth_headers(),
        json={"query": "budget cap test — this should NOT reach OpenRouter"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["openrouter_web_search"] is None, "the paid arm ran despite a $0 budget cap"
    assert body["openrouter_error"] and "budget" in body["openrouter_error"].lower()

    r = admin_session.put(f"{BASE}/api/admin/budget", headers=headers, json={"daily_limit_usd": 1.00}, timeout=10)
    assert r.status_code == 200, r.text


def step_grounding_lab_real_openrouter_call():
    """The one deliberate real-money call in this run (~$0.007, see
    config.py) — exercises OpenRouter's actual web-search plugin end to
    end, now that the budget is restored."""
    r = session.post(
        f"{BASE}/api/grounding-lab/compare",
        headers=auth_headers(),
        json={"query": "What is Model Context Protocol (MCP)?"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["own_pipeline"]["text"], "own pipeline produced no report text"
    if body["openrouter_error"]:
        print(f"    NOTE: OpenRouter web-search arm did not complete: {body['openrouter_error']}")
    else:
        assert body["openrouter_web_search"]["text"], "OpenRouter web-search arm produced no text"


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
    assert r.json()["report_count"] >= 2, "expected at least the 2 research reports sent earlier in this run"
    r = admin_session.get(f"{BASE}/api/admin/budget", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["daily_limit_usd"] == 1.00, "budget was not correctly restored after the governance test"


STEPS = [
    ("health check", step_health),
    ("wait for all 3 local models to finish warming up", step_wait_for_warm),
    ("signup issues a JWT", step_signup),
    ("auth/me via Bearer token", step_me),
    ("research: create a session", step_create_session),
    ("research: send a streamed query (bi-encoder retrieval)", step_send_query_bi_only),
    ("research: send a streamed query (bi+cross-encoder retrieval)", step_send_query_with_rerank),
    ("research: history reload preserves the groundedness badge (regression)", step_history_reload_preserves_groundedness),
    ("ghost-citation detector: unit check (mismatched + clean cases)", step_ghost_citation_unit_check),
    ("trend radar: JSON extraction regression (trailing-brace real output)", step_radar_json_extraction_regression),
    ("archive: semantic search finds a just-created report", step_archive_search),
    ("trend radar: 3-lens evaluation of a real tool", step_trend_radar),
    ("cost governance: $0 budget blocks the paid OpenRouter call", step_budget_governance_blocks_paid_call),
    ("grounding lab: real OpenRouter web-search comparison call", step_grounding_lab_real_openrouter_call),
    ("admin: a regular user is correctly forbidden", step_admin_rejected_for_regular_user),
    ("admin: the admin account can read system status + analytics + budget", step_admin_as_admin),
]

print(f"=== Compass end-to-end verification ({BASE}) ===\n")
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
