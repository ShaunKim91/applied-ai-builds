"""The Agent Console's core endpoint — starts a ReAct run and streams it
live as SSE. See agent/orchestrator.py for the shared loop engine this and
routers/approvals.py's resume path both drive.
"""
import datetime as dt
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..agent import react_loop
from ..agent.orchestrator import get_guardrail_settings, run_react_loop
from ..audit import log_action
from ..config import settings
from ..database import SessionLocal, get_db
from ..metrics import record_latency
from ..ml import embeddings, llm
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/agent", tags=["agent"])

# A run whose SSE stream is abandoned mid-flight (browser navigates away /
# tab closes) never gets another chance to advance — Starlette simply stops
# calling __anext__() on the generator, with no exception to catch. Real
# bug found and fixed in the predecessor Cradle PoC; the fix (a lazy
# staleness reaper) is applied here from the start.
_STALE_RUN_TIMEOUT_SECONDS = 180


def _reap_stale_runs(db: Session, org_id: int) -> None:
    cutoff = dt.datetime.utcnow() - dt.timedelta(seconds=_STALE_RUN_TIMEOUT_SECONDS)
    stale = db.query(models.AgentRun).filter(
        models.AgentRun.org_id == org_id, models.AgentRun.status == "RUNNING", models.AgentRun.updated_at < cutoff
    ).all()
    for run in stale:
        run.status = "FAILED"
        run.final_answer = "This run was abandoned (the client disconnected mid-stream) and was automatically marked failed after being stuck for over 3 minutes."
    if stale:
        db.commit()


def today_openrouter_spend(db: Session, org_id: int) -> float:
    start = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(models.AgentRun.cloud_cost_usd), 0.0))
        .filter(models.AgentRun.org_id == org_id, models.AgentRun.created_at >= start, models.AgentRun.cloud_cost_usd > 0)
        .scalar()
    )
    return float(total)


def get_daily_budget(db: Session, org_id: int) -> float:
    row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == org_id).first()
    return row.daily_limit_usd if row else settings.default_daily_budget_usd


def _run_dict(r: models.AgentRun) -> dict:
    return {
        "id": r.id,
        "question": r.question,
        "status": r.status,
        "final_answer": r.final_answer,
        "step_count": r.step_count,
        "spent_cost": r.spent_cost,
        "synth_mode": r.synth_mode,
        "cloud_cost_usd": r.cloud_cost_usd,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


def _step_dict(s: models.AgentStep) -> dict:
    return {"id": s.id, "step_number": s.step_number, "kind": s.kind, "content": s.content, "created_at": s.created_at.isoformat()}


@router.post("/runs", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def create_run(payload: dict, user: models.User = Depends(get_current_user)):
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    if len(question) > 1000:
        raise HTTPException(400, "question is too long (max 1000 characters)")

    db = SessionLocal()
    try:
        gset = get_guardrail_settings(db)
        run = models.AgentRun(
            org_id=user.org_id,
            owner_id=user.id,
            question=question,
            max_steps=gset.max_steps,
            cost_cap=gset.cost_cap,
            messages_json=json.dumps(react_loop.fewshot_messages() + [{"role": "user", "content": question}]),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    def event_stream():
        start = time.perf_counter()
        final_event = None
        for event in run_react_loop(run_id):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("done"):
                final_event = event
        if final_event is not None:
            latency_ms = (time.perf_counter() - start) * 1000
            record_latency("/api/agent/runs", latency_ms)
            _finalize(run_id, user, latency_ms)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _finalize(run_id: int, user: models.User, latency_ms: float) -> None:
    db2 = SessionLocal()
    try:
        run = db2.get(models.AgentRun, run_id)
        if not run:
            return
        log_action(db2, user, "agent.run", org_id=user.org_id, model_used=settings.local_agent_model, detail=f"status={run.status}", latency_ms=latency_ms)
        if run.status == "COMPLETED" and run.final_answer:
            try:
                vector = embeddings.embed_passage(f"{run.question}\n{run.final_answer}")
                vectorstore.upsert(f"run-{run.id}", f"{run.question}\n{run.final_answer}", vector, {"run_id": run.id, "question": run.question})
            except Exception:
                pass
    finally:
        db2.close()


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _reap_stale_runs(db, user.org_id)
    runs = db.query(models.AgentRun).filter(models.AgentRun.org_id == user.org_id).order_by(models.AgentRun.created_at.desc()).all()
    return [_run_dict(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = db.get(models.AgentRun, run_id)
    if not run or run.org_id != user.org_id:
        raise HTTPException(404, "Run not found")
    _reap_stale_runs(db, user.org_id)
    db.refresh(run)
    steps = db.query(models.AgentStep).filter(models.AgentStep.run_id == run_id).order_by(models.AgentStep.step_number.asc(), models.AgentStep.id.asc()).all()
    return {**_run_dict(run), "steps": [_step_dict(s) for s in steps]}


@router.post("/runs/{run_id}/escalate", dependencies=[Depends(verify_csrf)])
def escalate_run(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Model routing: hand the full trace to OpenRouter's qwen3-8b for one
    best-effort final answer. The escalation path has ZERO tool-calling
    capability — it cannot itself call issue_claim_payout. Any real payout
    must still flow back through the local ReAct loop + guardrail engine."""
    run = db.get(models.AgentRun, run_id)
    if not run or run.org_id != user.org_id:
        raise HTTPException(404, "Run not found")
    if run.status not in ("STOPPED_STEP_LIMIT", "COMPLETED"):
        raise HTTPException(409, f"Escalation isn't offered for a run in status '{run.status}'")

    budget = get_daily_budget(db, user.org_id)
    spent_today = today_openrouter_spend(db, user.org_id)
    estimated_cost = settings.openrouter_escalation_estimated_cost_usd
    if spent_today + estimated_cost > budget:
        raise HTTPException(402, f"Daily OpenRouter budget cap reached (${spent_today:.4f} spent of ${budget:.2f}) — escalation was skipped, not attempted silently.")

    messages = json.loads(run.messages_json)
    trace_lines = [f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"]
    trace_text = "\n".join(trace_lines)

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
    log_action(db, user, "agent.escalate", org_id=user.org_id, model_used=result["model"], latency_ms=call_latency_ms)
    return {"final_answer": result["text"], "model": result["model"], "cost_usd": estimated_cost}
