"""The Human-in-the-Loop approval queue — the one guardrail a typical
first-pass build implements as a scaffolded feature but never wires into
the shipped app. Threshold makes this real: an admin's approve/deny decision here
actually resumes the paused run via `agent/orchestrator.py`'s shared
generator, drained synchronously (no live SSE connection needed, since the
original requester's browser may be long gone by the time this is decided).
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..agent.orchestrator import run_react_loop
from ..audit import log_action
from ..database import get_db
from ..security import require_admin, verify_csrf

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _dict(a: models.ApprovalRequest) -> dict:
    return {
        "id": a.id,
        "run_id": a.run_id,
        "tool_name": a.tool_name,
        "tool_arg": a.tool_arg,
        "status": a.status,
        "reason": a.reason,
        "requested_at": a.requested_at.isoformat(),
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
    }


@router.get("")
def list_approvals(status: str = "pending", db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    q = (
        db.query(models.ApprovalRequest)
        .join(models.AgentRun, models.ApprovalRequest.run_id == models.AgentRun.id)
        .filter(models.AgentRun.org_id == admin.org_id)
    )
    if status != "all":
        q = q.filter(models.ApprovalRequest.status == status)
    rows = q.order_by(models.ApprovalRequest.requested_at.desc()).all()
    return [_dict(r) for r in rows]


class DecideIn(BaseModel):
    approve: bool
    reason: str = ""


@router.post("/{approval_id}/decide", dependencies=[Depends(verify_csrf)])
def decide(approval_id: int, payload: DecideIn, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    approval = db.get(models.ApprovalRequest, approval_id)
    if not approval:
        raise HTTPException(404, "Approval request not found")
    run = db.get(models.AgentRun, approval.run_id)
    if not run or run.org_id != admin.org_id:
        raise HTTPException(404, "Approval request not found")
    if approval.status != "pending":
        raise HTTPException(409, f"This request was already {approval.status}.")

    approval.status = "approved" if payload.approve else "denied"
    approval.reason = payload.reason
    approval.resolved_at = dt.datetime.utcnow()
    approval.resolved_by_id = admin.id
    db.commit()

    if payload.approve:
        from ..agent import guardrails

        result = guardrails.execute_tool(approval.tool_name, approval.tool_arg)
        injection = {
            "kind": "resumed",
            "content": f"[Approved by {admin.email}] {approval.tool_name}({approval.tool_arg})",
            "observation_message": f"Observation: {result}",
            "new_spent": run.spent_cost,
        }
    else:
        injection = {
            "kind": "resumed",
            "content": f"[Denied by {admin.email}] {approval.tool_name}({approval.tool_arg}) — {payload.reason or 'no reason given'}",
            "observation_message": f"Observation: This action was denied by a human reviewer. Reason: {payload.reason or 'none given'}. Do not retry it; consider an alternative or give a Final Answer explaining the situation.",
            "new_spent": run.spent_cost,
        }

    # Drained synchronously — no live SSE connection is attached, since the
    # original requester's browser may be long gone by the time an admin
    # gets around to this decision. Real fact, not fabricated: an approval
    # can genuinely happen minutes or hours after the run paused.
    final_event = None
    for event in run_react_loop(run.id, resume_injection=injection):
        if event.get("done"):
            final_event = event

    log_action(db, admin, "approval.decide", org_id=admin.org_id, detail=f"approval_id={approval_id} approve={payload.approve}")
    return {"approval": _dict(approval), "run_result": final_event}
