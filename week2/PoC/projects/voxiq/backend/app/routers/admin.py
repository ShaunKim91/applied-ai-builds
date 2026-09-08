import shutil

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..config import settings
from ..database import get_db
from ..ml import embeddings as emb_ml
from ..ml import llm as llm_ml
from ..ml import reranker as rerank_ml
from ..ml import sandbox as sandbox_ml
from ..ml import tokenizer_explorer
from ..ml import whisper_asr
from ..security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    target = db.get(models.User, user_id)
    if not target:
        return {"ok": False, "error": "not found"}
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    db.commit()
    return {"ok": True}


@router.get("/audit-log")
def audit_log(limit: int = 100, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user_email": l.user_email,
            "action": l.action,
            "model_used": l.model_used,
            "detail": l.detail,
            "latency_ms": round(l.latency_ms, 1),
            "status": l.status,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/system")
def system_status(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    def disk_usage(path: str):
        try:
            total, used, free = shutil.disk_usage(path)
            return {"total_gb": round(total / 1e9, 2), "used_gb": round(used / 1e9, 2), "free_gb": round(free / 1e9, 2)}
        except Exception:
            return None

    counts = {
        "users": db.query(func.count(models.User.id)).scalar(),
        "meetings": db.query(func.count(models.Meeting.id)).scalar(),
        "search_queries": db.query(func.count(models.SearchQuery.id)).scalar(),
        "sandbox_runs": db.query(func.count(models.SandboxRun.id)).scalar(),
        "audit_logs": db.query(func.count(models.AuditLog.id)).scalar(),
    }
    models_status = {
        "embeddings_loaded": emb_ml._model is not None,
        "reranker_loaded": rerank_ml._model is not None,
        "whisper_loaded": whisper_asr._model is not None,
        "local_llm_loaded": llm_ml._local_model is not None,
        "tokenizer_explorer_loaded": tokenizer_explorer._model is not None,
        "openrouter_key_present": llm_ml.openrouter_available(),
        "e2b_key_present": sandbox_ml.e2b_available(),
    }
    return {
        "counts": counts,
        "models": models_status,
        "vectorstore_backend": vectorstore.backend_name(),
        "sandbox_provider": settings.sandbox_provider,
        "disk": disk_usage(settings.data_dir),
        "data_dir": settings.data_dir,
    }
