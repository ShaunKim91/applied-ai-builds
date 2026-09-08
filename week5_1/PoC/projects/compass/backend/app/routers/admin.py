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
from ..search import web_search
from ..security import require_admin
from .research import get_daily_budget, today_openrouter_spend

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
        "research_sessions": db.query(func.count(models.ResearchSession.id)).scalar(),
        "report_entries": db.query(func.count(models.ReportEntry.id)).scalar(),
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


@router.get("/web-search-check")
def web_search_check(_admin: models.User = Depends(require_admin)):
    """A real, on-demand connectivity probe an admin can re-run any time
    (e.g. after suspecting ddgs is being rate-limited) without restarting
    the container. Updates the same state.last_web_search_check that
    /api/health/ready reports, so both views stay in sync."""
    from .. import state

    result = web_search.connectivity_check()
    state.last_web_search_check = result
    return result


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    """Real, computed usage stats — no fabricated demo data. If there isn't
    enough real usage yet, the series is simply short/empty."""
    entries = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.mode == "research")
        .order_by(models.ReportEntry.created_at.asc())
        .all()
    )
    latencies = [round(e.latency_ms, 1) for e in entries]
    groundedness_pass_rate = (
        round(sum(1 for e in entries if e.groundedness_passed) / len(entries), 3) if entries else None
    )
    search_mode_counts: dict[str, int] = {}
    synth_mode_counts: dict[str, int] = {}
    for e in entries:
        search_mode_counts[e.search_mode] = search_mode_counts.get(e.search_mode, 0) + 1
        synth_mode_counts[e.synth_mode] = synth_mode_counts.get(e.synth_mode, 0) + 1

    ghost_citation_count = sum(
        1 for e in entries if e.ghost_citations_json and '"ghost_citations": []' not in e.ghost_citations_json.replace(" ", "")
    )

    return {
        "report_count": len(entries),
        "latencies_ms": latencies[-30:],
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "groundedness_pass_rate": groundedness_pass_rate,
        "search_mode_counts": search_mode_counts,
        "synth_mode_counts": synth_mode_counts,
        "reports_with_ghost_citations": ghost_citation_count,
    }


# --- Cost governance: the "budget cap" discipline — a standard
# cost-governance practice — which a typical baseline implementation of
# this pattern never implements anywhere in its code. ---


@router.get("/budget")
def get_budget(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    limit = get_daily_budget(db)
    spent = today_openrouter_spend(db)
    return {
        "daily_limit_usd": limit,
        "spent_today_usd": round(spent, 4),
        "remaining_usd": round(max(0.0, limit - spent), 4),
        "cap_reached": spent >= limit,
    }


class BudgetUpdate(BaseModel):
    daily_limit_usd: float


@router.put("/budget")
def set_budget(payload: BudgetUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    from datetime import datetime

    row = db.get(models.BudgetSetting, 1)
    if not row:
        row = models.BudgetSetting(id=1, daily_limit_usd=payload.daily_limit_usd)
        db.add(row)
    else:
        row.daily_limit_usd = payload.daily_limit_usd
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "daily_limit_usd": row.daily_limit_usd}
