"""Admin console — users, hash-chained audit log (+ integrity verification),
runtime-adjustable guardrail settings (incl. the amount-aware payout
threshold), budget governance, real p50/p95/p99 metrics, and recent
structured errors. Every endpoint here requires the admin role."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..agent.orchestrator import get_guardrail_settings
from ..audit import verify_chain
from ..database import get_db
from ..metrics import snapshot
from ..security import require_admin, verify_csrf
from .agent import get_daily_budget, today_openrouter_spend

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


class GuardrailIn(BaseModel):
    allowed_tools: list[str]
    max_steps: int
    cost_cap: int
    payout_approval_threshold_usd: float


@router.get("/guardrails")
def get_guardrails(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    import json

    row = get_guardrail_settings(db)
    return {
        "allowed_tools": json.loads(row.allowed_tools_json),
        "max_steps": row.max_steps,
        "cost_cap": row.cost_cap,
        "payout_approval_threshold_usd": row.payout_approval_threshold_usd,
    }


@router.put("/guardrails", dependencies=[Depends(verify_csrf)])
def set_guardrails(payload: GuardrailIn, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    import json

    row = get_guardrail_settings(db)
    row.allowed_tools_json = json.dumps(payload.allowed_tools)
    row.max_steps = payload.max_steps
    row.cost_cap = payload.cost_cap
    row.payout_approval_threshold_usd = payload.payout_approval_threshold_usd
    db.commit()
    return {"ok": True}


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    total_runs = db.query(models.AgentRun).filter(models.AgentRun.org_id == admin.org_id).count()
    completed = db.query(models.AgentRun).filter(models.AgentRun.org_id == admin.org_id, models.AgentRun.status == "COMPLETED").count()
    guardrail_stops = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.org_id == admin.org_id, models.AgentRun.status.in_(["BLOCKED_PERMISSION", "STOPPED_STEP_LIMIT", "STOPPED_COST_CAP"]))
        .count()
    )
    pending_approvals = (
        db.query(models.ApprovalRequest)
        .join(models.AgentRun, models.ApprovalRequest.run_id == models.AgentRun.id)
        .filter(models.AgentRun.org_id == admin.org_id, models.ApprovalRequest.status == "pending")
        .count()
    )
    return {
        "total_runs": total_runs,
        "completed": completed,
        "guardrail_stops": guardrail_stops,
        "pending_approvals": pending_approvals,
        "users": db.query(models.User).filter(models.User.org_id == admin.org_id).count(),
    }
