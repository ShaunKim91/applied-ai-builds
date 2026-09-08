"""Multi-turn, streaming, web-search-grounded research — Compass's flagship
feature. Streamed as SSE-shaped lines over a POST request, same pattern as
Week4 Lucent's chat endpoint (a plain GET-only EventSource can't carry the
POST body a research query needs) and same FastAPI + StreamingResponse
gotcha handled the same way: the Depends()-injected DB session closes when
this function *returns*, before the generator body finishes streaming, so
any write that happens after the stream completes uses a fresh SessionLocal().
"""
import json
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..audit import log_action
from ..config import settings
from ..database import SessionLocal, get_db
from ..ml import ghost_citation, groundedness, llm
from ..pipeline import RESEARCH_SYSTEM_PROMPT, build_context_block, gather_sources
from ..security import get_current_user

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sessions = (
        db.query(models.ResearchSession)
        .filter(models.ResearchSession.owner_id == user.id)
        .order_by(models.ResearchSession.created_at.desc())
        .all()
    )
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]


@router.post("/sessions")
def create_session(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = models.ResearchSession(owner_id=user.id, title="New research")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "created_at": session.created_at.isoformat()}


def _entry_dict(e: models.ReportEntry) -> dict:
    # NOTE: `groundedness` is shaped to match the SAME nested object the
    # streaming 'done' SSE event sends below (`{passed, content_check:
    # {score}}`), not flat groundedness_score/groundedness_passed keys.
    # Week4's Lucent PoC shipped exactly that flat-vs-nested mismatch
    # between its streaming event and its history-reload endpoint
    # (debug/issue-02) — the badge worked live and silently vanished on
    # reload. Applying that lesson directly here instead of re-discovering
    # it.
    return {
        "id": e.id,
        "mode": e.mode,
        "query": e.query,
        "report_text": e.report_text,
        "sources": json.loads(e.sources_json),
        "ghost_citations": json.loads(e.ghost_citations_json),
        "radar": json.loads(e.radar_json),
        "search_mode": e.search_mode,
        "synth_mode": e.synth_mode,
        "groundedness": {"passed": e.groundedness_passed, "content_check": {"score": e.groundedness_score}},
        "cost_usd": e.cost_usd,
        "latency_ms": e.latency_ms,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/entries")
def list_entries(session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = db.get(models.ResearchSession, session_id)
    if not session or session.owner_id != user.id:
        raise HTTPException(404, "Session not found")
    entries = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.session_id == session_id)
        .order_by(models.ReportEntry.created_at.asc())
        .all()
    )
    return [_entry_dict(e) for e in entries]


def today_openrouter_spend(db: Session) -> float:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(models.ReportEntry.cost_usd), 0.0))
        .filter(models.ReportEntry.created_at >= start, models.ReportEntry.cost_usd > 0)
        .scalar()
    )
    return float(total or 0.0)


def get_daily_budget(db: Session) -> float:
    row = db.get(models.BudgetSetting, 1)
    return row.daily_limit_usd if row else settings.default_daily_budget_usd


class SendQueryRequest(BaseModel):
    query: str
    use_rerank: bool = True
    use_openrouter: bool = False


@router.post("/sessions/{session_id}/entries")
def send_query(
    session_id: int,
    payload: SendQueryRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    session = db.get(models.ResearchSession, session_id)
    if not session or session.owner_id != user.id:
        raise HTTPException(404, "Session not found")
    if session.title == "New research":
        session.title = payload.query[:60]
        db.commit()

    gathered = gather_sources(payload.query, use_rerank=payload.use_rerank)
    sources = gathered["sources"]
    context_block = build_context_block(sources)
    user_prompt = f"Search results:\n{context_block}\n\nQuestion: {payload.query}" if sources else payload.query
    synth_mode = "openrouter" if payload.use_openrouter else "local"
    start = time.perf_counter()

    def event_stream():
        full_text = []
        try:
            for fragment in llm.stream_generate(RESEARCH_SYSTEM_PROMPT, user_prompt, provider=synth_mode):
                full_text.append(fragment)
                yield f"data: {json.dumps({'delta': fragment})}\n\n"
        except Exception as exc:  # noqa: BLE001 — stream errors must reach the client
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return

        answer = "".join(full_text).strip()
        latency_ms = (time.perf_counter() - start) * 1000
        source_texts = [s["body"] for s in sources]
        source_urls = [s["href"] for s in sources]
        verdict = groundedness.verify(answer, source_texts)
        ghost = ghost_citation.check(answer, source_urls)

        db2 = SessionLocal()
        try:
            entry = models.ReportEntry(
                session_id=session_id,
                mode="research",
                query=payload.query,
                report_text=answer,
                sources_json=json.dumps(sources),
                ghost_citations_json=json.dumps(ghost),
                search_mode=gathered["search_mode"],
                synth_mode=synth_mode,
                groundedness_score=verdict["content_check"]["score"],
                groundedness_passed=verdict["passed"],
                cost_usd=0.0,  # local: genuinely free; openrouter LLM synth: not metered, see docs/guide.html
                latency_ms=latency_ms,
            )
            db2.add(entry)
            db2.commit()
            db2.refresh(entry)
            # Index this report into the vector store so Archive search can
            # find it later by meaning, not just keyword (see archive.py).
            if answer:
                from ..ml import embeddings

                vector = embeddings.embed_passage(f"{payload.query}\n{answer}")
                vectorstore.upsert(
                    f"report-{entry.id}",
                    f"{payload.query}\n{answer}",
                    vector,
                    {"report_id": entry.id, "session_id": session_id, "query": payload.query},
                )
            log_action(
                db2, user, "research.query",
                model_used=settings.local_llm_model if synth_mode == "local" else settings.openrouter_model,
                detail=f"search={gathered['search_mode']} rerank={payload.use_rerank}",
                latency_ms=latency_ms,
            )
            entry_id = entry.id
        finally:
            db2.close()

        yield f"data: {json.dumps({'done': True, 'entry_id': entry_id, 'sources': sources, 'search_mode': gathered['search_mode'], 'search_error': gathered['search_error'], 'ghost_citations': ghost, 'groundedness': verdict})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
