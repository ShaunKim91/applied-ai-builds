"""End-to-end smoke test for Lucent.

Exercises every major feature against a *running* instance over real HTTP —
no mocking, including actually consuming the streaming chat response as a
real client would (not just checking the endpoint returns 200) — and
prints a PASS/FAIL checklist, matching the verification discipline of the
Week1-3 PoCs.

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


def step_list_documents():
    r = session.get(f"{BASE}/api/documents", headers=auth_headers(), timeout=15)
    assert r.status_code == 200, r.text
    docs = r.json()
    assert len(docs) >= 50, f"expected the ~85 Federalist essays to be indexed, got {len(docs)} documents"
    languages = {d["language"] for d in docs}
    assert "ko" in languages, "Korean seed document was not indexed (a real, non-fatal bootstrap failure is possible — check bootstrap_step_errors)"


def step_upload_document():
    content = b"Lucent E2E test document. This paragraph exists purely to exercise the upload-and-index code path."
    r = session.post(
        f"{BASE}/api/documents/upload",
        headers=auth_headers(),
        files={"file": ("e2e_test.txt", content, "text/plain")},
        timeout=30,
    )
    assert r.status_code == 200, r.text


def step_create_session():
    r = session.post(f"{BASE}/api/chat/sessions", headers=auth_headers(), timeout=10)
    assert r.status_code == 200, r.text
    _ctx["session_id"] = r.json()["id"]


def _send_and_collect(content: str, use_rerank: bool = False, use_openrouter: bool = False, timeout: int = 90) -> dict:
    session_id = _ctx["session_id"]
    with session.post(
        f"{BASE}/api/chat/sessions/{session_id}/messages",
        headers=auth_headers(),
        json={"content": content, "use_rerank": use_rerank, "use_openrouter": use_openrouter},
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
        assert assembled, "assembled streamed answer was empty"
        return {"answer": assembled, **final_event}


def step_send_message_local():
    result = _send_and_collect("What does Federalist No. 51 say about checks and balances?")
    assert len(result["citations"]) > 0, "expected at least one retrieved source"
    assert "groundedness" in result


def step_send_message_with_rerank():
    result = _send_and_collect("What is the purpose of the judiciary according to the Federalist Papers?", use_rerank=True)
    assert len(result["citations"]) > 0


def step_cross_lingual_korean_query():
    """A real functional test of the multilingual embedding claim: a
    Korean-language question should retrieve at least one real source
    (Korean or English — both are on the same topic, so either is a
    legitimate, correct retrieval, not just the Korean document by ID
    match)."""
    result = _send_and_collect("연방주의자 논집은 무엇에 관한 문서인가요?")
    assert len(result["citations"]) > 0, "Korean-language query retrieved no sources at all"


def step_retrieval_compare():
    r = session.post(
        f"{BASE}/api/retrieval/compare",
        headers=auth_headers(),
        json={"query": "separation of powers between branches of government"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "bi_results" in body and "cross_results" in body
    assert len(body["bi_results"]) > 0 and len(body["cross_results"]) > 0


def step_admin_analytics_rejected_for_regular_user():
    r = session.get(f"{BASE}/api/admin/analytics", headers=auth_headers(), timeout=10)
    assert r.status_code == 403, "a regular user must NOT be able to read admin endpoints"


def step_admin_as_admin():
    admin_session = requests.Session()
    r = admin_session.post(
        f"{BASE}/api/auth/login",
        json={
            "email": os.environ.get("ADMIN_EMAIL", "admin@lucent.local"),
            "password": os.environ.get("ADMIN_PASSWORD", "ChangeMe123!"),
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = admin_session.get(f"{BASE}/api/admin/system", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "models" in body and "counts" in body
    r = admin_session.get(f"{BASE}/api/admin/analytics", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["message_count"] >= 3, "expected at least the 3 chat messages sent earlier in this run"


STEPS = [
    ("health check", step_health),
    ("wait for all 3 local models to finish warming up", step_wait_for_warm),
    ("signup issues a JWT", step_signup),
    ("auth/me via Bearer token", step_me),
    ("documents: seed corpus indexed (Federalist Papers + Korean Wikipedia)", step_list_documents),
    ("documents: upload a text file", step_upload_document),
    ("chat: create a session", step_create_session),
    ("chat: send a streamed message (bi-encoder retrieval)", step_send_message_local),
    ("chat: send a streamed message (bi+cross-encoder retrieval)", step_send_message_with_rerank),
    ("chat: cross-lingual Korean query retrieves real sources", step_cross_lingual_korean_query),
    ("retrieval: bi vs bi+cross comparison", step_retrieval_compare),
    ("admin: a regular user is correctly forbidden", step_admin_analytics_rejected_for_regular_user),
    ("admin: the admin account can read system status + analytics", step_admin_as_admin),
]

print(f"=== Lucent end-to-end verification ({BASE}) ===\n")
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
