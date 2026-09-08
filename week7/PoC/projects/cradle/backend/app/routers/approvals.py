"""The Human-in-the-Loop approval queue — the one guardrail a typical
baseline implementation builds as a class (`approval_required_tools`) but
never actually wires into its shipped app (stays an empty set). This
router makes it real: a pending request an admin can actually see and act
on, which actually resumes the paused agent run.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..agent import guardrails
from ..agent.orchestrator import run_react_loop
from ..audit import log_action
from ..config import settings
from ..database import get_db
from ..security import require_admin

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
def list_approvals(status: str = "pending", db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    q = db.query(models.ApprovalRequest)
    if status != "all":
        q = q.filter(models.ApprovalRequest.status == status)
    rows = q.order_by(models.ApprovalRequest.requested_at.desc()).all()
    return [_dict(a) for a in rows]


class DecideRequest(BaseModel):
    approve: bool
    reason: str = ""


@router.post("/{approval_id}/decide")
def decide(
    approval_id: int,
    payload: DecideRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    approval = db.get(models.ApprovalRequest, approval_id)
    if not approval:
        raise HTTPException(404, "Approval request not found")
    if approval.status != "pending":
        raise HTTPException(400, f"Already resolved as '{approval.status}'")

    run = db.get(models.AgentRun, approval.run_id)
    if not run or run.status != "AWAITING_APPROVAL":
        raise HTTPException(409, "The associated run is no longer awaiting approval")

    if payload.approve:
        result = guardrails.execute_tool(approval.tool_name, approval.tool_arg)
        cost = settings.default_tool_cost.get(approval.tool_name, 5)
        injection = {
            "kind": "observation",
            "content": result,
            "observation_message": f"Observation: {result}",
            "new_spent": run.spent_cost + cost,
        }
        approval.status = "approved"
    else:
        denial = f"Request denied by reviewer.{' Reason: ' + payload.reason if payload.reason else ''}"
        injection = {
            "kind": "observation",
            "content": denial,
            "observation_message": f"Observation: {denial}",
            "new_spent": run.spent_cost,
        }
        approval.status = "denied"

    approval.reason = payload.reason
    approval.resolved_at = datetime.utcnow()
    approval.resolved_by_id = admin.id
    db.commit()

    # Resumes synchronously — an approval can arrive long after the
    # original streamed request ended, so there's no live connection to
    # push SSE events to; drain the shared orchestrator generator and
    # return whichever terminal 'done' event it produces (COMPLETED,
    # another AWAITING_APPROVAL if the agent calls a second gated tool, a
    # guardrail stop, etc.) — never a fabricated/assumed outcome.
    final_event = None
    for event in run_react_loop(run.id, resume_injection=injection):
        if event.get("done"):
            final_event = event

    # latency_ms intentionally left at its default 0.0 here (see debug/issue-06,
    # which fixed the two AI-call audit entries): how long an admin took to
    # review a request isn't a system performance metric worth timing, unlike
    # an actual model/API call's duration.
    log_action(db, admin, "approval.decide", detail=f"approval_id={approval_id} approve={payload.approve}")
    return {"approval": _dict(approval), "run_result": final_event}
