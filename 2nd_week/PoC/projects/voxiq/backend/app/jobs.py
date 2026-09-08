"""Minimal in-process background job manager.

Diffusion image generation takes seconds-to-minutes on CPU, so it runs in a
background thread and the frontend polls GET /api/generate/jobs/{id}.

This intentionally avoids adding Redis/Celery for the PoC (keeps the stack to
a single container on 16GB-RAM student laptops) — see architecture.md's
"Production Scaling" section for how this would become a real task queue in
a commercial deployment.
"""
import threading
import time
import uuid
from typing import Callable

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _create_job(kind: str) -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": kind,
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }
    return job_id


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _run(job_id: str, fn: Callable):
    with _lock:
        _jobs[job_id]["status"] = "running"
    try:
        result = fn()
        with _lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
    except Exception as exc:  # noqa: BLE001 - surfaced to the client via /jobs/{id}
        with _lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(exc)


def submit(kind: str, fn: Callable) -> str:
    job_id = _create_job(kind)
    thread = threading.Thread(target=_run, args=(job_id, fn), daemon=True)
    thread.start()
    return job_id
