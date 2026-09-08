"""Vendor & Tool Adoption Radar — the old Compass "Trend Radar" (D4's 3-lens
cost/security/approval-friction framework) reframed explicitly as "should
Fenwick Mutual's claims ops team adopt this AI/InsurTech vendor tool."
Uses REAL live web search (search/web_search.py) since evaluating a real
vendor tool is genuinely real-world research — unlike claims/jurisdiction
research, which never touches the live web (see search/jurisdictions.py)."""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, pipeline
from ..audit import log_action
from ..database import get_db
from ..metrics import record_latency
from ..ml import llm
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/radar", tags=["radar"])

RADAR_SYSTEM_PROMPT = (
    "You are evaluating an AI or InsurTech vendor tool for adoption by a "
    "regional P&C insurer's claims operations team. Using ONLY the "
    "numbered sources given, respond with a single JSON object with keys "
    "\"cost\", \"security\", \"approval_friction\" — each an object with "
    "\"verdict\" (one of Low, Medium, High, or \"Insufficient evidence\") "
    "and \"reasoning\" (a short string citing [n] markers). Output ONLY "
    "the JSON object, nothing else."
)


@router.post("/evaluate", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def evaluate(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    topic = (payload.get("topic") or "").strip()
    if not topic:
        raise HTTPException(400, "topic is required")
    start = time.perf_counter()

    sources = pipeline.gather_radar_sources(topic)
    context_block = pipeline.build_context_block(sources)
    fragments = list(
        llm.stream_generate(RADAR_SYSTEM_PROMPT, f"Sources:\n{context_block}\n\nVendor/tool to evaluate: {topic}", max_new_tokens=400)
    )
    raw = "".join(fragments)
    radar = pipeline.extract_first_json_object(raw)
    extraction_failed = radar is None

    entry = models.ReportEntry(
        org_id=user.org_id,
        owner_id=user.id,
        mode="radar",
        query=topic,
        report_text=raw,
        radar_json=json.dumps(radar or {"extraction_failed": True, "raw": raw}),
        sources_json=json.dumps(sources),
        source_trust_json=json.dumps([{"url": s.get("href", ""), "tier": pipeline.classify_source_trust(s)} for s in sources]),
        search_mode="ddgs",
        synth_mode="local",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    latency_ms = (time.perf_counter() - start) * 1000
    record_latency("/api/radar/evaluate", latency_ms)
    log_action(db, user, "radar.evaluate", org_id=user.org_id, model_used="Qwen2.5-0.5B-Instruct", detail=topic, latency_ms=latency_ms)

    return {
        "id": entry.id,
        "topic": topic,
        "radar": radar,
        "extraction_failed": extraction_failed,
        "raw_text": raw if extraction_failed else None,
        "sources": sources,
    }


@router.get("/history")
def history(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = (
        db.query(models.ReportEntry)
        .filter(models.ReportEntry.org_id == user.org_id, models.ReportEntry.mode == "radar")
        .order_by(models.ReportEntry.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {"id": r.id, "topic": r.query, "radar": json.loads(r.radar_json), "created_at": r.created_at.isoformat()} for r in rows
    ]
