"""The Agent Console's core endpoint — starts a ReAct run and streams it
live as SSE. See agent/orchestrator.py for the shared loop engine this and
routers/approvals.py's resume path both drive.
"""
import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..agent import react_loop
from ..agent.orchestrator import get_guardrail_settings, run_react_loop
from ..audit import log_action
from ..config import settings
from ..database import get_db
from ..ml import embeddings, llm
from ..security import get_current_user

router = APIRouter(prefix="/api/agent", tags=["agent"])


def today_openrouter_spend(db: Session) -> float:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(models.AgentRun.cloud_cost_usd), 0.0))
        .filter(models.AgentRun.created_at >= start, models.AgentRun.cloud_cost_usd > 0)
        .scalar()
    )
    return float(total or 0.0)


def get_daily_budget(db: Session) -> float:
    row = db.get(models.BudgetSetting, 1)
    return row.daily_limit_usd if row else settings.default_daily_budget_usd


class NewRunRequest(BaseModel):
    question: str


def _run_dict(r: models.AgentRun) -> dict:
    return {
        "id": r.id,
        "question": r.question,
        "status": r.status,
        "final_answer": r.final_answer,
        "step_count": r.step_count,
        "spent_cost": r.spent_cost,
        "max_steps": r.max_steps,
        "cost_cap": r.cost_cap,
        "synth_mode": r.synth_mode,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


def _step_dict(s: models.AgentStep) -> dict:
    return {"id": s.id, "step_number": s.step_number, "kind": s.kind, "content": s.content, "created_at": s.created_at.isoformat()}


# A run left in "RUNNING" this long with no update is not still legitimately
# generating — it's a run whose SSE stream was abandoned mid-flight (e.g.
# the browser navigated away or the tab was closed while the agent loop was
# between steps). Found via real testing: a client disconnect during
# StreamingResponse iteration simply stops the server-side generator from
# ever being advanced again — there is no exception to catch, so nothing
# updates that run's status, and it would otherwise sit at "RUNNING"
# forever: never completable, never escalatable (escalate requires
# STOPPED_STEP_LIMIT/COMPLETED), invisible to History (never embedded), and
# permanently skewing the Dashboard/Analytics counts. See debug/issue-03.
_STALE_RUN_TIMEOUT_SECONDS = 180


def _reap_stale_runs(db: Session, owner_id: int) -> None:
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(seconds=_STALE_RUN_TIMEOUT_SECONDS)
    stale = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.owner_id == owner_id, models.AgentRun.status == "RUNNING", models.AgentRun.updated_at < cutoff)
        .all()
    )
    for run in stale:
        run.status = "FAILED"
        run.final_answer = "This run was abandoned (the connection was interrupted before it finished) and could not be resumed."
    if stale:
        db.commit()


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _reap_stale_runs(db, user.id)
    runs = db.query(models.AgentRun).filter(models.AgentRun.owner_id == user.id).order_by(models.AgentRun.created_at.desc()).all()
    return [_run_dict(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = db.get(models.AgentRun, run_id)
    if not run or run.owner_id != user.id:
        raise HTTPException(404, "Run not found")
    _reap_stale_runs(db, user.id)
    db.refresh(run)
    steps = db.query(models.AgentStep).filter(models.AgentStep.run_id == run_id).order_by(models.AgentStep.step_number.asc(), models.AgentStep.id.asc()).all()
    return {**_run_dict(run), "steps": [_step_dict(s) for s in steps]}


@router.post("/runs")
def create_run(payload: NewRunRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    gset = get_guardrail_settings(db)
    messages = react_loop.fewshot_messages() + [{"role": "user", "content": payload.question}]
    run = models.AgentRun(
        owner_id=user.id,
        question=payload.question,
        status="RUNNING",
        max_steps=gset.max_steps,
        cost_cap=gset.cost_cap,
        messages_json=json.dumps(messages),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id

    def event_stream():
        for event in run_react_loop(run_id):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("done"):
                _finalize(run_id, user)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/runs/{run_id}/escalate")
def escalate_run(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Model routing (a well-documented 2025-2026 trend, rarely implemented
    in a typical baseline build): when the local agent stalls (step limit,
    repeated format errors) or the user just wants a second opinion, hand
    its full trace to OpenRouter's larger qwen3-8b for one best-effort
    final answer — not a second independent tool-calling loop, budget-gated
    the same way Week5_1's Compass PoC gates its own OpenRouter calls."""
    run = db.get(models.AgentRun, run_id)
    if not run or run.owner_id != user.id:
        raise HTTPException(404, "Run not found")
    if run.status not in ("STOPPED_STEP_LIMIT", "COMPLETED"):
        raise HTTPException(409, f"Escalation isn't offered for a run in status '{run.status}'")

    budget = get_daily_budget(db)
    spent_today = today_openrouter_spend(db)
    estimated_cost = settings.openrouter_escalation_estimated_cost_usd
    if spent_today + estimated_cost > budget:
        raise HTTPException(
            402,
            f"Daily OpenRouter budget cap reached (${spent_today:.4f} spent of ${budget:.2f}) — "
            f"escalation was skipped, not attempted silently.",
        )

    messages = json.loads(run.messages_json)
    trace_lines = [f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"]
    trace_text = "\n".join(trace_lines)

    # See debug/issue-06: latency_ms used to be a hardcoded 0.0 everywhere in
    # this file — the audit trail's own "how long did this take" column was
    # dead weight, never once reflecting a real duration despite existing
    # specifically for that. Timed for real here.
    call_start = time.perf_counter()
    result = llm.escalate_to_cloud(run.question, trace_text)
    call_latency_ms = (time.perf_counter() - call_start) * 1000
    run.synth_mode = "openrouter"
    run.cloud_cost_usd = estimated_cost
    if run.status != "COMPLETED":
        run.final_answer = result["text"]
        run.status = "COMPLETED"
    db.add(models.AgentStep(run_id=run.id, step_number=run.step_count + 1, kind="cloud_escalation", content=result["text"]))
    db.commit()
    log_action(db, user, "agent.escalate", model_used=result["model"], latency_ms=call_latency_ms)
    return {"final_answer": result["text"], "model": result["model"], "cost_usd": estimated_cost}


def _finalize(run_id: int, user: models.User) -> None:
    """Runs once a stream reaches a 'done' event: logs the audit entry and,
    for a completed run, indexes it into the archive vector store — mirrors
    the exact pattern (fresh session, post-stream side effects) validated
    in the Week4/14_1 PoCs."""
    from ..database import SessionLocal

    db2 = SessionLocal()
    try:
        run = db2.get(models.AgentRun, run_id)
        if not run:
            return
        # See debug/issue-06. A run's own created_at/updated_at (already
        # real, and load-bearing for the stale-run reaper in issue-03) is
        # the right measurement for "how long did this whole agent run
        # take" — not just its last step, which is all a call-local timer
        # here could see.
        run_latency_ms = (run.updated_at - run.created_at).total_seconds() * 1000 if run.updated_at and run.created_at else 0.0
        log_action(db2, user, "agent.run", model_used="Qwen2.5-0.5B-Instruct", detail=f"status={run.status}", latency_ms=run_latency_ms)
        if run.status == "COMPLETED" and run.final_answer:
            vector = embeddings.embed_passage(f"{run.question}\n{run.final_answer}")
            vectorstore.upsert(
                f"run-{run.id}",
                f"{run.question}\n{run.final_answer}",
                vector,
                {"run_id": run.id, "question": run.question},
            )
    finally:
        db2.close()
