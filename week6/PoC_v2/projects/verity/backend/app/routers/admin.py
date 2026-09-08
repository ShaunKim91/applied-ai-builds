"""Admin console — users, hash-chained audit log (+ integrity verification),
budget governance, real p50/p95/p99 latency metrics, and recent structured
errors. Every endpoint here requires the admin role."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import verify_chain
from ..database import get_db
from ..metrics import snapshot
from ..security import require_admin, verify_csrf
from .research import get_daily_budget, today_openrouter_spend

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.User).filter(models.User.org_id == admin.org_id).order_by(models.User.created_at.asc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "locked": bool(u.locked_until),
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.get("/audit-log")
def audit_log(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.org_id == admin.org_id)
        .order_by(models.AuditLog.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": r.id,
            "user_email": r.user_email,
            "action": r.action,
            "model_used": r.model_used,
            "detail": r.detail,
            "latency_ms": round(r.latency_ms, 1),
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/audit-log/verify")
def audit_log_verify(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    return verify_chain(db)


@router.get("/errors")
def recent_errors(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.ErrorLog).order_by(models.ErrorLog.id.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "request_id": r.request_id,
            "route": r.route,
            "method": r.method,
            "error_class": r.error_class,
            "message": r.message,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/metrics")
def metrics(admin: models.User = Depends(require_admin)):
    return snapshot()


class BudgetIn(BaseModel):
    daily_limit_usd: float


@router.get("/budget")
def get_budget(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    return {"daily_limit_usd": get_daily_budget(db, admin.org_id), "spent_today_usd": today_openrouter_spend(db, admin.org_id)}


@router.put("/budget", dependencies=[Depends(verify_csrf)])
def set_budget(payload: BudgetIn, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == admin.org_id).first()
    if not row:
        row = models.BudgetSetting(org_id=admin.org_id)
        db.add(row)
    row.daily_limit_usd = payload.daily_limit_usd
    db.commit()
    return {"daily_limit_usd": row.daily_limit_usd}


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    total_reports = db.query(models.ReportEntry).filter(models.ReportEntry.org_id == admin.org_id).count()
    by_mode = {}
    for mode in ("quick", "precedent_brief", "radar"):
        by_mode[mode] = db.query(models.ReportEntry).filter(models.ReportEntry.org_id == admin.org_id, models.ReportEntry.mode == mode).count()
    ghost_count = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.org_id == admin.org_id)
        .all()
    )
    import json as _json

    ghost_failed = sum(1 for r in ghost_count if not _json.loads(r.ghost_citations_json or "{}").get("passed", True))
    return {
        "total_reports": total_reports,
        "by_mode": by_mode,
        "ghost_citation_failures": ghost_failed,
        "users": db.query(models.User).filter(models.User.org_id == admin.org_id).count(),
        "cat_events": db.query(models.CatEvent).filter(models.CatEvent.org_id == admin.org_id).count(),
    }
