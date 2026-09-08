"""The Workspace's backing API: create/list/search cases, the live SSE
messaging endpoint (the one place `chains.orchestrator`'s prepare/stream/
finalize split is actually driven end-to-end), OpenRouter escalation, memory
conflict resolution, and the purge/right-to-erasure action.
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..audit import log_action
from ..chains import orchestrator
from ..config import settings
from ..database import SessionLocal, get_db
from ..metrics import record_latency
from ..ml import embeddings, llm
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _case_dict(c: models.CallerCase) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "status": c.status,
        "case_summary": c.case_summary,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _turn_dict(t: models.ConversationTurn) -> dict:
    return {"id": t.id, "role": t.role, "content": t.content, "redacted": t.redacted, "tool_name": t.tool_name, "created_at": t.created_at.isoformat()}


def _fact_dict(f: models.MemoryFact) -> dict:
    return {"field_name": f.field_name, "field_value": f.field_value, "confidence": f.confidence, "updated_at": f.updated_at.isoformat()}


def _conflict_dict(c: models.MemoryConflictLog) -> dict:
    return {
        "id": c.id,
        "field_name": c.field_name,
        "old_value": c.old_value,
        "new_value": c.new_value,
        "resolution": c.resolution,
        "created_at": c.created_at.isoformat(),
    }


@router.post("", dependencies=[Depends(verify_csrf)])
def create_case(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    title = (payload.get("title") or "").strip() or "Untitled case"
    case = models.CallerCase(org_id=user.org_id, owner_id=user.id, title=title)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_dict(case)


@router.get("")
def list_cases(q: str = "", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if q.strip():
        vector = embeddings.embed_query(q)
        result = vectorstore.query(vector, n_results=10)
        ids = result.get("ids", [[]])[0]
        case_ids = [int(i.split("-")[1]) for i in ids if i.startswith("case-")]
        if not case_ids:
            return []
        rows = db.query(models.CallerCase).filter(models.CallerCase.id.in_(case_ids), models.CallerCase.org_id == user.org_id).all()
        by_id = {r.id: r for r in rows}
        return [_case_dict(by_id[i]) for i in case_ids if i in by_id]
    rows = db.query(models.CallerCase).filter(models.CallerCase.org_id == user.org_id).order_by(models.CallerCase.updated_at.desc()).all()
    return [_case_dict(r) for r in rows]


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.get(models.CallerCase, case_id)
    if not case or case.org_id != user.org_id:
        raise HTTPException(404, "Case not found")
    turns = db.query(models.ConversationTurn).filter(models.ConversationTurn.case_id == case_id).order_by(models.ConversationTurn.id.asc()).all()
    facts = db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case_id).all()
    conflicts = (
        db.query(models.MemoryConflictLog)
        .filter(models.MemoryConflictLog.case_id == case_id, models.MemoryConflictLog.resolution == "pending_confirmation")
        .order_by(models.MemoryConflictLog.created_at.desc())
        .all()
    )
    return {
        **_case_dict(case),
        "turns": [_turn_dict(t) for t in turns],
        "facts": [_fact_dict(f) for f in facts],
        "pending_conflicts": [_conflict_dict(c) for c in conflicts],
    }


@router.post("/{case_id}/close", dependencies=[Depends(verify_csrf)])
def close_case(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.get(models.CallerCase, case_id)
    if not case or case.org_id != user.org_id:
        raise HTTPException(404, "Case not found")
    case.status = "closed"
    db.commit()
    return _case_dict(case)


@router.post("/{case_id}/conflicts/{conflict_id}/resolve", dependencies=[Depends(verify_csrf)])
def resolve_conflict(case_id: int, conflict_id: int, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    resolution = payload.get("resolution")
    if resolution not in ("accepted_new", "kept_old"):
        raise HTTPException(400, "resolution must be 'accepted_new' or 'kept_old'")
    from ..chains.extraction import resolve_conflict as do_resolve

    result = do_resolve(db, conflict_id, resolution, user.id)
    if result is None:
        raise HTTPException(404, "Conflict not found or already resolved")
    log_action(db, user, "memory.conflict_resolved", org_id=user.org_id, detail=f"conflict_id={conflict_id} resolution={resolution}")
    return _conflict_dict(result)


@router.post("/{case_id}/messages", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def send_message(case_id: int, payload: dict, user: models.User = Depends(get_current_user)):
    message_text = (payload.get("message") or "").strip()
    if not message_text:
        raise HTTPException(400, "message is required")
    if len(message_text) > 2000:
        raise HTTPException(400, "message is too long (max 2000 characters)")

    db = SessionLocal()
    try:
        case = db.get(models.CallerCase, case_id)
        if not case or case.org_id != user.org_id:
            raise HTTPException(404, "Case not found")
        ctx = orchestrator.prepare_turn(db, case, user, message_text)
    finally:
        db.close()

    def event_stream():
        start = time.perf_counter()
        yield f"data: {json.dumps({'router': ctx.router_result.decision.model_dump(), 'tool_result': ctx.tool_result_text})}\n\n"
        fragments: list[str] = []
        for fragment in orchestrator.stream_turn_reply(ctx):
            fragments.append(fragment)
            yield f"data: {json.dumps({'delta': fragment})}\n\n"
        reply_text = "".join(fragments).strip()
        latency_ms = (time.perf_counter() - start) * 1000
        record_latency("/api/cases/messages", latency_ms)

        db2 = SessionLocal()
        try:
            ai_turn = orchestrator.finalize_turn(db2, ctx, user, reply_text, latency_ms)
            case2 = db2.get(models.CallerCase, case_id)
            try:
                vector = embeddings.embed_passage(f"{case2.title}\n{case2.case_summary}")
                vectorstore.upsert(f"case-{case_id}", f"{case2.title}\n{case2.case_summary}", vector, {"case_id": case_id})
            except Exception:
                pass
            yield f"data: {json.dumps({'done': True, 'reply_id': ai_turn.id, 'reply': reply_text})}\n\n"
        finally:
            db2.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{case_id}/escalate", dependencies=[Depends(verify_csrf)])
def escalate_case(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.get(models.CallerCase, case_id)
    if not case or case.org_id != user.org_id:
        raise HTTPException(404, "Case not found")

    budget_row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == user.org_id).first()
    budget = budget_row.daily_limit_usd if budget_row else settings.default_daily_budget_usd
    import datetime as dt
    from sqlalchemy import func

    start_of_day = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    spent_today = (
        db.query(func.count(models.AuditLog.id))
        .filter(models.AuditLog.org_id == user.org_id, models.AuditLog.action == "case.escalate", models.AuditLog.created_at >= start_of_day)
        .scalar()
        or 0
    ) * settings.openrouter_escalation_estimated_cost_usd
    if spent_today + settings.openrouter_escalation_estimated_cost_usd > budget:
        raise HTTPException(402, f"Daily OpenRouter budget cap reached (${spent_today:.4f} spent of ${budget:.2f}) — escalation was skipped, not attempted silently.")

    turns = db.query(models.ConversationTurn).filter(models.ConversationTurn.case_id == case_id).order_by(models.ConversationTurn.id.asc()).all()
    trace_text = "\n".join(f"{t.role}: {t.content}" for t in turns[-10:])
    context = f"Case summary: {case.case_summary or '(none yet)'}\n\nRecent turns:\n{trace_text}"

    call_start = time.perf_counter()
    result = llm.escalate_to_cloud(case.title, context)
    call_latency_ms = (time.perf_counter() - call_start) * 1000

    log_action(db, user, "case.escalate", org_id=user.org_id, model_used=result["model"], latency_ms=call_latency_ms)
    return {"text": result["text"], "model": result["model"], "cost_usd": settings.openrouter_escalation_estimated_cost_usd}


@router.post("/{case_id}/purge", dependencies=[Depends(verify_csrf)])
def purge_case_endpoint(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = db.get(models.CallerCase, case_id)
    if not case or case.org_id != user.org_id:
        raise HTTPException(404, "Case not found")
    retention = orchestrator.purge_case(db, case, user)
    return {
        "ok": True,
        "case_id": retention.case_id,
        "turns_deleted": retention.turns_deleted,
        "facts_deleted": retention.facts_deleted,
    }
