"""Trend Radar — turns a 3-lens tool-evaluation framework (Cost /
Security / Approval-friction) into a real, working feature: search the web
for a tool/trend, then have the local LLM extract a structured verdict per
lens, grounded strictly in what was actually found. A typical baseline
implementation of this pattern only *discusses* this kind of framework in
a doc; it is never implemented as code there — this is a concrete piece of
engineering depth beyond that baseline.

Uses the same free local pipeline as ordinary research by default (no extra
cost) — this feature does not require the OpenRouter web-search plugin.
"""
import json
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action
from ..config import settings
from ..database import get_db
from ..ml import llm
from ..pipeline import RADAR_SYSTEM_PROMPT, build_context_block, gather_sources, parse_radar_json
from ..security import get_current_user

router = APIRouter(prefix="/api/trend-radar", tags=["trend-radar"])


class RadarRequest(BaseModel):
    topic: str


@router.post("/evaluate")
def evaluate(payload: RadarRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    start = time.perf_counter()
    gathered = gather_sources(payload.topic, use_rerank=True)
    context_block = build_context_block(gathered["sources"])
    prompt = f"Search results about \"{payload.topic}\":\n{context_block}" if gathered["sources"] else payload.topic

    raw_text = "".join(llm.stream_generate(RADAR_SYSTEM_PROMPT, prompt, provider="local")).strip()
    radar = parse_radar_json(raw_text)
    latency_ms = (time.perf_counter() - start) * 1000

    entry = models.ReportEntry(
        session_id=None,
        mode="trend_radar",
        query=payload.topic,
        report_text=raw_text,
        sources_json=json.dumps(gathered["sources"]),
        ghost_citations_json="{}",
        radar_json=json.dumps(radar) if radar else "null",
        search_mode=gathered["search_mode"],
        synth_mode="local",
        cost_usd=0.0,
        latency_ms=latency_ms,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, user, "trend_radar.evaluate", model_used=settings.local_llm_model, detail=payload.topic[:80], latency_ms=latency_ms)

    return {
        "entry_id": entry.id,
        "topic": payload.topic,
        "radar": radar,
        "extraction_failed": radar is None,
        "raw_text": raw_text,
        "sources": gathered["sources"],
        "search_mode": gathered["search_mode"],
        "latency_ms": round(latency_ms, 1),
    }


@router.get("/history")
def history(limit: int = 20, db: Session = Depends(get_db), _user: models.User = Depends(get_current_user)):
    entries = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.mode == "trend_radar")
        .order_by(models.ReportEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "topic": e.query,
            "radar": json.loads(e.radar_json),
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
