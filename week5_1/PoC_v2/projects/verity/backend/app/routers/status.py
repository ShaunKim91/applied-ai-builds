"""A public (no-auth) status page — model warm state, vector-store
reachability, OpenRouter reachability (boolean only — never leaking key
presence details beyond configured/not), uptime, current p95. A real
commercial product publishes this; none of the prior products in this
series did."""
import time

from fastapi import APIRouter

from .. import state, vectorstore
from ..metrics import snapshot
from ..ml import llm

router = APIRouter(prefix="/api/status", tags=["status"])

_start_time = time.monotonic()


@router.get("")
def public_status():
    readiness = state.readiness()
    try:
        vectorstore.count()
        vector_ok = True
    except Exception:
        vector_ok = False
    research_metrics = next((m for m in snapshot() if m["route"] == "/api/research/query"), None)
    return {
        "app": "Verity",
        "uptime_seconds": round(time.monotonic() - _start_time),
        "models_warm": readiness["all_warm"],
        "vector_store_reachable": vector_ok,
        "openrouter_configured": llm.openrouter_available(),
        "research_p95_ms": research_metrics["p95_ms"] if research_metrics else None,
    }
