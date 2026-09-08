from fastapi import APIRouter

from .. import state

router = APIRouter()


@router.get("/api/health")
def health():
    """Liveness — the process is up and can serve requests. Always fast,
    never blocks on model loading (used by Docker's HEALTHCHECK)."""
    return {"status": "ok"}


@router.get("/api/health/ready")
def ready():
    """Readiness — reports real per-model loaded status (no auth required;
    non-sensitive operational data) plus whether the startup bootstrap
    thread has finished. `all_warm` is intentionally gated on the 3 local
    models only, NOT on live web-search connectivity — a `ddgs` rate-limit
    is an expected, handled failure mode (falls back to mock results, see
    search/web_search.py), not a reason to report the whole app as unready.
    Search connectivity is still reported here for visibility, and can be
    re-checked on demand via GET /api/admin/web-search-check."""
    from ..ml import embeddings, llm, reranker

    models = {
        "embeddings": embeddings._model is not None,
        "reranker": reranker._model is not None,
        "local_llm": llm._local_model is not None,
    }
    return {
        "bootstrap_complete": state.bootstrap_complete.is_set(),
        "bootstrap_step_errors": state.bootstrap_step_errors,
        "models": models,
        "web_search": state.last_web_search_check,
        "all_warm": all(models.values()),
    }
