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
    thread has finished. See Week1 PoC's debug/issue-03/issue-06 for why
    this exists and why each bootstrap step is isolated."""
    from ..agent import react_loop
    from ..ml import embeddings

    models = {
        "embeddings": embeddings._model is not None,
        "local_agent": react_loop._model is not None,
    }
    return {
        "bootstrap_complete": state.bootstrap_complete.is_set(),
        "bootstrap_step_errors": state.bootstrap_step_errors,
        "models": models,
        "all_warm": all(models.values()),
    }
