"""End-to-end smoke test for Parchment.

Exercises every major feature against a *running* instance over real HTTP —
no mocking — and prints a PASS/FAIL checklist, matching the verification
discipline of the Week1 ("CommerceIQ") and Week2 ("VoxIQ") PoCs.

Run from inside the container (has network access + all deps installed):
    docker compose exec -T app python verify_e2e.py
or via the convenience wrapper:
    ./scripts/verify_e2e.sh
"""
import io
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


def step_list_receipt_samples():
    r = session.get(f"{BASE}/api/receipts/samples", timeout=30)
    assert r.status_code == 200
    samples = r.json()["samples"]
    assert len(samples) >= 1
    _ctx["receipt_sample"] = samples[0]["filename"]


def step_extract_receipt_sample():
    filename = _ctx["receipt_sample"]
    r = session.post(f"{BASE}/api/receipts/extract-sample/{filename}", headers=auth_headers(), timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["ocr_text"], str) and len(body["ocr_text"]) > 0, "OCR returned no text"
    assert isinstance(body["vlm_answer"], str) and len(body["vlm_answer"]) > 0, "VLM returned no answer"


def step_extract_receipt_sample_again_is_flagged_duplicate():
    """Processing the exact same sample a second time should trip the
    near-duplicate detector (ml/dedupe.py) — a real functional check of the
    vector-store-backed dedupe feature, not just that the endpoint responds."""
    filename = _ctx["receipt_sample"]
    r = session.post(f"{BASE}/api/receipts/extract-sample/{filename}", headers=auth_headers(), timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["duplicate_of_id"] is not None, "reprocessing the identical sample should be flagged as a duplicate"


def step_extract_receipt_upload():
    # A tiny synthetic receipt-like image, generated on the fly, purely to
    # exercise the upload code path end-to-end.
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (400, 150), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    d.text((10, 10), "E2E TEST STORE", fill="black", font=font)
    d.text((10, 60), "Widget   $9.99", fill="black", font=font)
    d.text((10, 100), "TOTAL: $9.99", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = session.post(
        f"{BASE}/api/receipts/extract",
        headers=auth_headers(),
        files={"file": ("e2e_test.png", buf, "image/png")},
        timeout=60,
    )
    assert r.status_code == 200, r.text


def step_summarize_pdf_sample():
    r = session.post(f"{BASE}/api/pdfs/summarize-sample", headers=auth_headers(), json={"use_openrouter": False}, timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["summary_text"], str) and len(body["summary_text"]) > 0, "summary was empty"
    assert body["numeric_check_passed"], f"numeric cross-check failed: {body['numeric_check_detail']}"


def step_parse_html_table():
    sample = session.get(f"{BASE}/api/tables/sample", timeout=10).json()
    r = session.post(f"{BASE}/api/tables/parse", headers=auth_headers(), json={"url": sample["url"]}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["table_count"] >= 1
    assert len(body["tables"][0]["rows"]) > 0


def step_library_view():
    r = session.get(f"{BASE}/api/library", headers=auth_headers(), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert body["duplicate_count"] >= 1, "expected at least one duplicate flagged from the earlier step"


def step_admin_rejected_for_regular_user():
    r = session.get(f"{BASE}/api/admin/users", headers=auth_headers(), timeout=10)
    assert r.status_code == 403, "a regular user must NOT be able to read admin endpoints"


def step_admin_as_admin():
    admin_session = requests.Session()
    r = admin_session.post(
        f"{BASE}/api/auth/login",
        json={
            "email": os.environ.get("ADMIN_EMAIL", "admin@parchment.local"),
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
    ("wait for all 5 local models to finish warming up", step_wait_for_warm),
    ("signup issues a JWT", step_signup),
    ("auth/me via Bearer token", step_me),
    ("receipts: list samples", step_list_receipt_samples),
    ("receipts: extract sample (OCR + VLM side by side)", step_extract_receipt_sample),
    ("receipts: reprocessing the same sample is flagged as duplicate", step_extract_receipt_sample_again_is_flagged_duplicate),
    ("receipts: extract an uploaded image", step_extract_receipt_upload),
    ("pdfs: summarize sample (numeric cross-check)", step_summarize_pdf_sample),
    ("tables: parse sample HTML page", step_parse_html_table),
    ("library: combined view shows the flagged duplicate", step_library_view),
    ("admin: a regular user is correctly forbidden", step_admin_rejected_for_regular_user),
    ("admin: the admin account can read system status", step_admin_as_admin),
]

print(f"=== Parchment end-to-end verification ({BASE}) ===\n")
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
