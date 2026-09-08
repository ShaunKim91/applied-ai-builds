from fastapi import APIRouter

from .. import state

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    return state.readiness()
