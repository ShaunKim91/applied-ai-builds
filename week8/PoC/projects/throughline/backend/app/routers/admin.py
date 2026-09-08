"""Admin console — users, hash-chained audit log (+ integrity verification),
runtime-adjustable memory governance (window size, redaction toggle), the
full memory-conflict log (not just pending items — every overwrite decision,
per this project's own "log every guardrail decision" principle), the
retention/purge trail, budget governance, and real p50/p95/p99 metrics.
Every endpoint here requires the admin role."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import verify_chain
from ..chains.orchestrator import get_memory_settings
from ..database import get_db
from ..metrics import snapshot
from ..security import require_admin, verify_csrf

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.User).filter(models.User.org_id == admin.org_id).order_by(models.User.created_at.asc()).all()
    return [
        {"id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role, "is_active": u.is_active, "locked": bool(u.locked_until), "created_at": u.created_at.isoformat()}
        for u in rows
    ]


@router.get("/audit-log")
def audit_log(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.AuditLog).filter(models.AuditLog.org_id == admin.org_id).order_by(models.AuditLog.id.desc()).limit(200).all()
    return [
        {"id": r.id, "user_email": r.user_email, "action": r.action, "model_used": r.model_used, "detail": r.detail, "latency_ms": round(r.latency_ms, 1), "status": r.status, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@router.get("/audit-log/verify")
def audit_log_verify(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    return verify_chain(db)


@router.get("/errors")
def recent_errors(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.ErrorLog).order_by(models.ErrorLog.id.desc()).limit(100).all()
    return [
        {"id": r.id, "request_id": r.request_id, "route": r.route, "method": r.method, "error_class": r.error_class, "message": r.message, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@router.get("/metrics")
def metrics(admin: models.User = Depends(require_admin)):
    return snapshot()


class BudgetIn(BaseModel):
    daily_limit_usd: float


@router.get("/budget")
def get_budget(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == admin.org_id).first()
    from ..config import settings

    return {"daily_limit_usd": row.daily_limit_usd if row else settings.default_daily_budget_usd}


@router.put("/budget", dependencies=[Depends(verify_csrf)])
def set_budget(payload: BudgetIn, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == admin.org_id).first()
    if not row:
        row = models.BudgetSetting(org_id=admin.org_id)
        db.add(row)
    row.daily_limit_usd = payload.daily_limit_usd
    db.commit()
    return {"daily_limit_usd": row.daily_limit_usd}


class MemorySettingIn(BaseModel):
    window_turns: int
    redaction_enabled: bool


@router.get("/memory-settings")
def get_memory_settings_route(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    row = get_memory_settings(db, admin.org_id)
    return {"window_turns": row.window_turns, "redaction_enabled": row.redaction_enabled}


@router.put("/memory-settings", dependencies=[Depends(verify_csrf)])
def set_memory_settings(payload: MemorySettingIn, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    row = get_memory_settings(db, admin.org_id)
    row.window_turns = payload.window_turns
    row.redaction_enabled = payload.redaction_enabled
    db.commit()
    return {"window_turns": row.window_turns, "redaction_enabled": row.redaction_enabled}


@router.get("/memory-conflicts")
def memory_conflicts(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = (
        db.query(models.MemoryConflictLog)
        .join(models.CallerCase, models.MemoryConflictLog.case_id == models.CallerCase.id)
        .filter(models.CallerCase.org_id == admin.org_id)
        .order_by(models.MemoryConflictLog.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": r.id, "case_id": r.case_id, "field_name": r.field_name, "old_value": r.old_value, "new_value": r.new_value,
            "resolution": r.resolution, "created_at": r.created_at.isoformat(), "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in rows
    ]


@router.get("/retention-requests")
def retention_requests(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.query(models.RetentionRequest).filter(models.RetentionRequest.org_id == admin.org_id).order_by(models.RetentionRequest.id.desc()).limit(200).all()
    return [
        {
            "id": r.id, "case_id": r.case_id, "case_title_snapshot": r.case_title_snapshot,
            "turns_deleted": r.turns_deleted, "facts_deleted": r.facts_deleted, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    total_cases = db.query(models.CallerCase).filter(models.CallerCase.org_id == admin.org_id).count()
    open_cases = db.query(models.CallerCase).filter(models.CallerCase.org_id == admin.org_id, models.CallerCase.status == "open").count()
    total_turns = (
        db.query(models.ConversationTurn)
        .join(models.CallerCase, models.ConversationTurn.case_id == models.CallerCase.id)
        .filter(models.CallerCase.org_id == admin.org_id)
        .count()
    )
    pending_conflicts = (
        db.query(models.MemoryConflictLog)
        .join(models.CallerCase, models.MemoryConflictLog.case_id == models.CallerCase.id)
        .filter(models.CallerCase.org_id == admin.org_id, models.MemoryConflictLog.resolution == "pending_confirmation")
        .count()
    )
    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "total_turns": total_turns,
        "pending_conflicts": pending_conflicts,
        "users": db.query(models.User).filter(models.User.org_id == admin.org_id).count(),
    }
