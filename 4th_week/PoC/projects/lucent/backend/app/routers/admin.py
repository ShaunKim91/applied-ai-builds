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
        "documents": db.query(func.count(models.Document.id)).scalar(),
        "chat_sessions": db.query(func.count(models.ChatSession.id)).scalar(),
        "chat_messages": db.query(func.count(models.ChatMessage.id)).scalar(),
        "audit_logs": db.query(func.count(models.AuditLog.id)).scalar(),
    }
    models_status = {
        "embeddings_loaded": emb_ml._model is not None,
        "reranker_loaded": rerank_ml._model is not None,
        "local_llm_loaded": llm_ml._local_model is not None,
        "openrouter_key_present": llm_ml.openrouter_available(),
    }
    return {
        "counts": counts,
        "models": models_status,
        "vectorstore_backend": vectorstore.backend_name(),
        "disk": disk_usage(settings.data_dir),
        "data_dir": settings.data_dir,
    }


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    """Real, computed usage stats for the admin dashboard's charts — no
    fabricated demo data. If there isn't enough real usage yet, the series
    is simply short/empty; the frontend renders whatever real data exists."""
    assistant_msgs = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.role == "assistant")
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    latencies = [round(m.latency_ms, 1) for m in assistant_msgs]
    groundedness_pass_rate = (
        round(sum(1 for m in assistant_msgs if m.groundedness_passed) / len(assistant_msgs), 3)
        if assistant_msgs
        else None
    )
    retrieval_mode_counts: dict[str, int] = {}
    for m in assistant_msgs:
        retrieval_mode_counts[m.retrieval_mode] = retrieval_mode_counts.get(m.retrieval_mode, 0) + 1

    doc_counts_by_language: dict[str, int] = {}
    for d in db.query(models.Document).all():
        doc_counts_by_language[d.language] = doc_counts_by_language.get(d.language, 0) + 1

    return {
        "message_count": len(assistant_msgs),
        "latencies_ms": latencies[-30:],  # most recent 30, for a sparkline/bar chart
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "groundedness_pass_rate": groundedness_pass_rate,
        "retrieval_mode_counts": retrieval_mode_counts,
        "documents_by_language": doc_counts_by_language,
    }
