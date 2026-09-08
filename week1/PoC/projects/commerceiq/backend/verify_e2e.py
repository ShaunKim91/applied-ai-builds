"""End-to-end smoke test for CommerceIQ.

Exercises every major feature against a *running* instance over real HTTP —
no mocking — and prints a PASS/FAIL checklist. This is the project's
"검수과정을 단계별로 검증" script: it proves the whole stack (auth, all 5 AI
models, DB writes, vector search, admin authorization) actually works, not
just that the server boots.

Run from inside the container (has network access + all deps installed):
    docker compose exec -T app python backend/verify_e2e.py
or via the convenience wrapper:
    ./scripts/verify_e2e.sh
"""
import io
import os
import sys
import time
import uuid

import requests
from PIL import Image

BASE = f"http://localhost:{os.environ.get('PORT', '8000')}"
session = requests.Session()
token = {"value": None}
results: list[tuple[str, bool, float, str]] = []


def check(name: str, fn) -> None:
    start = time.perf_counter()
    try:
        fn()
        results.append((name, True, time.perf_counter() - start, ""))
    except Exception as exc:  # noqa: BLE001 — we want every failure captured, not raised
        results.append((name, False, time.perf_counter() - start, str(exc)))


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {token['value']}"} if token["value"] else {}


def step_health():
    r = session.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200 and r.json()["status"] == "ok"


def step_wait_for_warm():
    """Waits for the background bootstrap thread (all 4 local models +
    both public datasets) to finish, so the timed feature steps below
    measure real feature latency instead of getting blamed for a slow
    first-time model download racing against them. On a slow connection
    this alone can take several minutes — that's expected, not a failure;
    see debug/issue-02 for the incident this step was added to prevent."""
    deadline = time.time() + 1200  # 20 minutes ceiling for a genuinely slow link
    last_print = 0.0
    while time.time() < deadline:
        r = session.get(f"{BASE}/api/health/ready", timeout=10)
        body = r.json()
        if body.get("all_warm"):
            return
        # Dataset-download steps (as opposed to model-load steps) are allowed
        # to fail here without aborting the wait — see debug/issue-06: each
        # dataset auto-retries the next time a real request needs it (e.g.
        # the forecast/vision-samples endpoints), and model warm-up is fully
        # independent of dataset warm-up. We only bail out early if bootstrap
        # finished a full pass AND a *model* step is still failing.
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
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
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


def step_vision_samples():
    r = session.get(f"{BASE}/api/vision/samples", timeout=60)
    assert r.status_code == 200
    samples = r.json()["samples"]
    assert len(samples) >= 1, "no sample images available (data bootstrap may still be running)"
    step_vision_samples.filename = samples[0]["filename"]  # type: ignore[attr-defined]


def step_vision_classify_sample():
    filename = step_vision_samples.filename  # type: ignore[attr-defined]
    r = session.post(f"{BASE}/api/vision/classify-sample/{filename}", headers=auth_headers(), timeout=180)
    assert r.status_code == 200, r.text
    assert len(r.json()["predictions"]) >= 1


def step_vision_classify_upload():
    img = Image.new("RGB", (64, 64), color=(200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = session.post(
        f"{BASE}/api/vision/classify",
        headers=auth_headers(),
        files={"file": ("test.png", buf, "image/png")},
        timeout=60,
    )
    assert r.status_code == 200, r.text


def step_generate():
    r = session.post(
        f"{BASE}/api/generate",
        headers=auth_headers(),
        json={"prompt": "a red apple on a white background, product photo", "steps": 4, "guidance_scale": 5.0},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    for _ in range(200):  # up to ~10 minutes; step_wait_for_warm should make this fast in practice
        job = session.get(f"{BASE}/api/generate/jobs/{job_id}", timeout=15).json()
        if job["status"] == "done":
            return
        if job["status"] == "failed":
            raise AssertionError(f"generation job failed: {job['error']}")
        time.sleep(3)
    raise AssertionError("generation job did not finish in time")


def step_forecast():
    r = session.post(
        f"{BASE}/api/forecast/run",
        headers=auth_headers(),
        json={"horizon_days": 14, "use_openrouter": False, "lang": "en"},
        timeout=600,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["forecast"]) == 14
    assert isinstance(body["ai_insight"], str) and len(body["ai_insight"]) > 0


def step_search():
    r = session.post(f"{BASE}/api/search", headers=auth_headers(), json={"query": "fresh fruit", "top_k": 5}, timeout=30)
    assert r.status_code == 200, r.text


def step_admin_rejected_for_regular_user():
    r = session.get(f"{BASE}/api/admin/users", headers=auth_headers(), timeout=10)
    assert r.status_code == 403, "a regular user must NOT be able to read admin endpoints"


def step_admin_as_admin():
    admin_session = requests.Session()
    r = admin_session.post(
        f"{BASE}/api/auth/login",
        json={
            "email": os.environ.get("ADMIN_EMAIL", "admin@commerceiq.local"),
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


STEPS = [
    ("health check", step_health),
    ("wait for all 4 local models to finish warming up", step_wait_for_warm),
    ("signup issues a JWT", step_signup),
    ("auth/me via Bearer token", step_me),
    ("vision: list sample catalog images", step_vision_samples),
    ("vision: classify sample image (ViT-tiny)", step_vision_classify_sample),
    ("vision: classify an uploaded image", step_vision_classify_upload),
    ("generate: submit + poll a diffusion job (tiny-sd)", step_generate),
    ("forecast: Holt-Winters + AI insight (local Qwen2.5-0.5B)", step_forecast),
    ("search: semantic query (e5-small + vector store)", step_search),
    ("admin: a regular user is correctly forbidden", step_admin_rejected_for_regular_user),
    ("admin: the admin account can read system status", step_admin_as_admin),
]

print(f"=== CommerceIQ end-to-end verification ({BASE}) ===\n")
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
