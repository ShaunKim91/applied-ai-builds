import json
import shutil

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..agent import react_loop, tools
from ..agent.orchestrator import get_guardrail_settings
from ..config import settings
from ..database import get_db
from ..ml import embeddings as emb_ml
from ..ml import llm as llm_ml
from ..security import require_admin
from .agent import get_daily_budget, today_openrouter_spend

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
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
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
        "agent_runs": db.query(func.count(models.AgentRun.id)).scalar(),
        "approval_requests": db.query(func.count(models.ApprovalRequest.id)).scalar(),
        "audit_logs": db.query(func.count(models.AuditLog.id)).scalar(),
    }
    models_status = {
        "embeddings_loaded": emb_ml._model is not None,
        "local_agent_loaded": react_loop._model is not None,
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
    """Real, computed usage stats — no fabricated demo data."""
    runs = db.query(models.AgentRun).order_by(models.AgentRun.created_at.asc()).all()
    status_counts: dict[str, int] = {}
    step_counts = []
    for r in runs:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        if r.status in ("COMPLETED",):
            step_counts.append(r.step_count)

    return {
        "run_count": len(runs),
        "status_counts": status_counts,
        "avg_steps_to_completion": round(sum(step_counts) / len(step_counts), 2) if step_counts else None,
        "step_counts": [r.step_count for r in runs][-30:],
        "blocked_permission_count": status_counts.get("BLOCKED_PERMISSION", 0),
        "awaiting_approval_count": status_counts.get("AWAITING_APPROVAL", 0),
    }


# --- Guardrail governance (allowed tools, step limit, cost cap) ---


@router.get("/guardrails")
def get_guardrails(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    gset = get_guardrail_settings(db)
    return {
        "allowed_tools": json.loads(gset.allowed_tools_json),
        "available_tools": sorted(tools.ALLOWED_TOOLS.keys()),
        "hitl_tools": sorted(tools.HITL_TOOL_NAMES),
        "max_steps": gset.max_steps,
        "cost_cap": gset.cost_cap,
        "tool_cost": settings.default_tool_cost,
    }


class GuardrailUpdate(BaseModel):
    allowed_tools: list[str]
    max_steps: int
    cost_cap: int


@router.put("/guardrails")
def set_guardrails(payload: GuardrailUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    from datetime import datetime

    # Never allow delete_customer_data (or any unknown name) onto the
    # allowlist via this endpoint — the whole point of the decoy tool is
    # that it can never legitimately end up here.
    valid = set(tools.ALLOWED_TOOLS.keys())
    cleaned = sorted(set(payload.allowed_tools) & valid)
    gset = get_guardrail_settings(db)
    gset.allowed_tools_json = json.dumps(cleaned)
    gset.max_steps = max(1, payload.max_steps)
    gset.cost_cap = max(1, payload.cost_cap)
    gset.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "allowed_tools": cleaned, "max_steps": gset.max_steps, "cost_cap": gset.cost_cap}


# --- Cost governance for OpenRouter model-routing escalation (Compass pattern, reused) ---


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
