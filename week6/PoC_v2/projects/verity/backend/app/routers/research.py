"""The Research/Precedent-Brief streaming endpoint — Verity's core feature.

Grounding pipeline: gather fictional-jurisdiction sources -> rerank -> build
a numbered context block -> stream a local (or opt-in OpenRouter) synthesis
-> verify groundedness + ghost citations + fraud signals + source trust,
all computed AFTER the stream completes and persisted alongside it.
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, pipeline, vectorstore
from ..audit import log_action
from ..config import settings
from ..database import SessionLocal, get_db
from ..metrics import record_latency
from ..ml import embeddings, fraud_signals, ghost_citation, groundedness, llm
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/research", tags=["research"])


def today_openrouter_spend(db: Session, org_id: int) -> float:
    start = __import__("datetime").datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(models.ReportEntry.cost_usd), 0.0))
        .filter(models.ReportEntry.org_id == org_id, models.ReportEntry.created_at >= start, models.ReportEntry.cost_usd > 0)
        .scalar()
    )
    return float(total)


def get_daily_budget(db: Session, org_id: int) -> float:
    row = db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == org_id).first()
    return row.daily_limit_usd if row else settings.default_daily_budget_usd


class SessionIn(BaseModel):
    title: str = ""
    claim_number: str = ""
    jurisdiction: str = ""
    cat_event_id: int | None = None


@router.post("/sessions", dependencies=[Depends(verify_csrf)])
def create_session(payload: SessionIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = models.ResearchSession(
        org_id=user.org_id,
        owner_id=user.id,
        title=payload.title or payload.claim_number or "Untitled research",
        claim_number=payload.claim_number,
        jurisdiction=payload.jurisdiction,
        cat_event_id=payload.cat_event_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_dict(session)


def _session_dict(s: models.ResearchSession) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "claim_number": s.claim_number,
        "jurisdiction": s.jurisdiction,
        "cat_event_id": s.cat_event_id,
        "created_at": s.created_at.isoformat(),
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Org-wide activity snapshot for the Dashboard — deliberately lighter
    than /api/admin/analytics and available to any team member, not just
    admins, since knowing how much research the team has produced is a
    normal part of a claims analyst's own job, not an admin concern."""
    total = db.query(models.ReportEntry).filter(models.ReportEntry.org_id == user.org_id).count()
    by_mode = {
        mode: db.query(models.ReportEntry).filter(models.ReportEntry.org_id == user.org_id, models.ReportEntry.mode == mode).count()
        for mode in ("quick", "precedent_brief", "radar")
    }
    ghost_failed = 0
    for r in db.query(models.ReportEntry).filter(models.ReportEntry.org_id == user.org_id).all():
        gh = json.loads(r.ghost_citations_json or "{}")
        if not gh.get("passed", True):
            ghost_failed += 1
    cat_events = db.query(models.CatEvent).filter(models.CatEvent.org_id == user.org_id).count()
    return {"total_reports": total, "by_mode": by_mode, "ghost_citation_failures": ghost_failed, "cat_events": cat_events}


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = (
        db.query(models.ResearchSession)
        .filter(models.ResearchSession.org_id == user.org_id)
        .order_by(models.ResearchSession.created_at.desc())
        .all()
    )
    return [_session_dict(r) for r in rows]


def _entry_dict(e: models.ReportEntry) -> dict:
    return {
        "id": e.id,
        "session_id": e.session_id,
        "mode": e.mode,
        "query": e.query,
        "report_text": e.report_text,
        "brief": json.loads(e.brief_json) if e.brief_json else {},
        "sources": json.loads(e.sources_json),
        "source_trust": json.loads(e.source_trust_json),
        "ghost_citations": json.loads(e.ghost_citations_json),
        "fraud_signals": json.loads(e.fraud_signals_json),
        "groundedness_score": e.groundedness_score,
        "jurisdiction": e.jurisdiction,
        "claim_number": e.claim_number,
        "search_mode": e.search_mode,
        "synth_mode": e.synth_mode,
        "cost_usd": e.cost_usd,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/entries")
def list_entries(session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = db.get(models.ResearchSession, session_id)
    if not session or session.org_id != user.org_id:
        raise HTTPException(404, "Session not found")
    rows = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.session_id == session_id)
        .order_by(models.ReportEntry.created_at.asc())
        .all()
    )
    return [_entry_dict(r) for r in rows]


def _parse_brief(text: str) -> dict:
    sections = {"issue": "", "governing_authority": "", "facts_applied": "", "recommendation": "", "sources": ""}
    label_map = {
        "Issue:": "issue",
        "Governing Authority:": "governing_authority",
        "Facts Applied:": "facts_applied",
        "Recommendation:": "recommendation",
        "Sources:": "sources",
    }
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        matched = next((label for label in label_map if stripped.startswith(label)), None)
        if matched:
            current = label_map[matched]
            sections[current] = stripped[len(matched) :].strip()
        elif current:
            sections[current] += ("\n" + stripped if sections[current] else stripped)
    return sections


@router.post("/query", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def run_query(payload: dict, user: models.User = Depends(get_current_user)):
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    if len(query) > 2000:
        raise HTTPException(400, "query is too long (max 2000 characters)")
    mode = payload.get("mode", "quick")
    if mode not in ("quick", "precedent_brief"):
        raise HTTPException(400, "mode must be 'quick' or 'precedent_brief'")
    jurisdiction = payload.get("jurisdiction") or None
    claim_number = payload.get("claim_number", "")
    session_id = payload.get("session_id")
    use_openrouter = bool(payload.get("use_openrouter", False))
    org_id = user.org_id

    def event_stream():
        db = SessionLocal()
        start = time.perf_counter()
        try:
            sources = pipeline.gather_claims_sources(query, jurisdiction)
            context_block = pipeline.build_context_block(sources)
            system_prompt = llm.BRIEF_SYSTEM_PROMPT if mode == "precedent_brief" else llm.GROUNDING_SYSTEM_PROMPT
            user_content = f"Sources:\n{context_block}\n\nQuestion: {query}"

            synth_mode = "local"
            cost_usd = 0.0
            fragments: list[str] = []

            if use_openrouter:
                budget = get_daily_budget(db, org_id)
                spent = today_openrouter_spend(db, org_id)
                est_cost = 0.0008
                if spent + est_cost > budget:
                    yield f"data: {json.dumps({'error': 'Daily OpenRouter budget cap reached — escalation skipped, not attempted silently.'})}\n\n"
                    return
                result = llm.escalate_to_cloud(query, context_block)
                fragments = [result["text"]]
                yield f"data: {json.dumps({'delta': result['text']})}\n\n"
                synth_mode = "openrouter"
                cost_usd = est_cost
            else:
                for fragment in llm.stream_generate(system_prompt, user_content):
                    fragments.append(fragment)
                    yield f"data: {json.dumps({'delta': fragment})}\n\n"

            report_text = "".join(fragments).strip()
            source_texts = [s.get("body", "") for s in sources]
            source_urls = [s.get("href", "") for s in sources]

            gr = groundedness.verify(report_text, source_texts)
            ghosts = ghost_citation.check(report_text, source_urls)
            # See ghost_citation.py's check_entities() docstring: the
            # sentence-similarity groundedness check alone can be fooled by
            # a hallucinated-but-topically-plausible named authority (a real
            # measured failure this build found — "The Federal Insurance
            # Office" scored a perfect 1.0 groundedness against fictional
            # Cedermoor sources). This is a second, independent check merged
            # into the same ghost_citations payload the UI already renders.
            entity_check = ghost_citation.check_entities(report_text, source_texts)
            ghosts["passed"] = ghosts["passed"] and entity_check["passed"]
            ghosts["unverified_entities"] = entity_check["unverified_entities"]
            frauds = fraud_signals.check(f"{query}\n{report_text}")
            trust = [{"url": s.get("href", ""), "tier": pipeline.classify_source_trust(s)} for s in sources]
            brief = _parse_brief(report_text) if mode == "precedent_brief" else {}

            entry = models.ReportEntry(
                org_id=org_id,
                owner_id=user.id,
                session_id=session_id,
                mode=mode,
                query=query,
                report_text=report_text,
                brief_json=json.dumps(brief),
                sources_json=json.dumps(sources),
                source_trust_json=json.dumps(trust),
                ghost_citations_json=json.dumps(ghosts),
                fraud_signals_json=json.dumps(frauds),
                groundedness_score=gr["score"],
                jurisdiction=jurisdiction or "",
                claim_number=claim_number,
                search_mode="fictional_corpus",
                synth_mode=synth_mode,
                cost_usd=cost_usd,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)

            try:
                vector = embeddings.embed_passage(f"{query}\n{report_text}")
                vectorstore.upsert(
                    f"entry-{entry.id}",
                    f"{query}\n{report_text}",
                    vector,
                    {"entry_id": entry.id, "claim_number": claim_number, "jurisdiction": jurisdiction or ""},
                )
            except Exception:
                pass

            latency_ms = (time.perf_counter() - start) * 1000
            record_latency("/api/research/query", latency_ms)
            log_action(
                db,
                user,
                "research.query",
                org_id=org_id,
                model_used=settings.openrouter_model if use_openrouter else settings.local_llm_model,
                detail=f"mode={mode} jurisdiction={jurisdiction}",
                latency_ms=latency_ms,
            )

            yield f"data: {json.dumps({'done': True, 'entry': _entry_dict(entry)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
