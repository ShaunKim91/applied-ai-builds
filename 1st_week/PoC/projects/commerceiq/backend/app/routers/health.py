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
    this is non-sensitive operational data, the same technique
    routers/admin.py uses for its authenticated /admin/system view) plus
    whether the one-time startup bootstrap thread has finished.

    Scripts (like scripts/verify_e2e.sh) can poll this BEFORE exercising
    features, so a slow first-time model download shows up as "still
    warming up" instead of looking like a feature timeout/failure.
    """
    from ..ml import diffusion, embeddings, llm, vision  # local import: avoid loading torch at process start

    models = {
        "vision": vision._model is not None,
        "diffusion": diffusion._pipe is not None,
        "embeddings": embeddings._model is not None,
        "local_llm": llm._local_model is not None,
    }
    return {
        "bootstrap_complete": state.bootstrap_complete.is_set(),
        # Per-step failures from the LAST bootstrap pass (see debug/issue-06)
        # — a step can still fail here and yet "models" above shows it
        # loaded, if a later request lazily retried it successfully; this
        # dict is diagnostic history, not a live blocker.
        "bootstrap_step_errors": state.bootstrap_step_errors,
        "models": models,
        "all_warm": all(models.values()),
    }
