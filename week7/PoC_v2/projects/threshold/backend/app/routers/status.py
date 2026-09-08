"""A public (no-auth) status page — model warm state, vector-store
reachability, OpenRouter reachability (boolean only), uptime, current p95."""
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
    agent_metrics = next((m for m in snapshot() if m["route"] == "/api/agent/runs"), None)
    return {
        "app": "Threshold",
        "uptime_seconds": round(time.monotonic() - _start_time),
        "models_warm": readiness["all_warm"],
        "vector_store_reachable": vector_ok,
        "openrouter_configured": llm.openrouter_available(),
        "agent_p95_ms": agent_metrics["p95_ms"] if agent_metrics else None,
    }
