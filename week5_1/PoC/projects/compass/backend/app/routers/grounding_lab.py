"""Grounding Lab — compares Compass's own pipeline (ddgs search -> bi+cross
rerank -> local synthesis) against OpenRouter's fully-managed web-search
plugin (one call does live search AND generation, server-side). Extends the
comparison spirit of Week4's Retrieval Lab (bi- vs. bi+cross-encoder) one
level up: comparing two entire retrieval *strategies*, not just two
rerankers within one pipeline.

The OpenRouter side costs real money (~$0.007/request, see config.py) and
is gated by the same daily budget cap the Admin cost-governance panel
configures — reusing routers/research.py's spend/budget helpers so there is
exactly one source of truth for "how much has been spent today."
"""
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action
from ..config import settings
from ..database import get_db
from ..ml import ghost_citation, llm
from ..pipeline import RESEARCH_SYSTEM_PROMPT, build_context_block, gather_sources
from ..security import get_current_user
from .research import get_daily_budget, today_openrouter_spend

router = APIRouter(prefix="/api/grounding-lab", tags=["grounding-lab"])


class CompareRequest(BaseModel):
    query: str


@router.post("/compare")
def compare(payload: CompareRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # --- Arm 1: Compass's own pipeline (free, local) ---
    own_start = time.perf_counter()
    gathered = gather_sources(payload.query, use_rerank=True)
    own_context = build_context_block(gathered["sources"])
    own_prompt = f"Search results:\n{own_context}\n\nQuestion: {payload.query}" if gathered["sources"] else payload.query
    own_answer = "".join(llm.stream_generate(RESEARCH_SYSTEM_PROMPT, own_prompt, provider="local")).strip()
    own_latency_ms = (time.perf_counter() - own_start) * 1000
    own_urls = [s["href"] for s in gathered["sources"]]
    own_ghost = ghost_citation.check(own_answer, own_urls)

    own_entry = models.ReportEntry(
        session_id=None,
        mode="grounding_lab",
        query=payload.query,
        report_text=own_answer,
        sources_json="[]",
        ghost_citations_json="{}",
        search_mode=gathered["search_mode"],
        synth_mode="local",
        cost_usd=0.0,
        latency_ms=own_latency_ms,
    )

    # --- Arm 2: OpenRouter's managed web-search plugin (real cost, budget-gated) ---
    budget = get_daily_budget(db)
    spent_today = today_openrouter_spend(db)
    estimated_cost = settings.openrouter_web_search_estimated_cost_usd
    openrouter_arm = None
    openrouter_error = None

    if spent_today + estimated_cost > budget:
        openrouter_error = (
            f"Daily OpenRouter budget cap reached (${spent_today:.3f} spent of ${budget:.2f}) — "
            f"the paid web-search comparison call was skipped, not attempted silently."
        )
    else:
        try:
            or_start = time.perf_counter()
            raw = llm.openrouter_web_search(payload.query, RESEARCH_SYSTEM_PROMPT)
            or_latency_ms = (time.perf_counter() - or_start) * 1000
            or_urls = [c["url"] for c in raw["citations"]]
            or_ghost = ghost_citation.check(raw["text"], or_urls)
            openrouter_arm = {
                "text": raw["text"],
                "citations": raw["citations"],
                "latency_ms": round(or_latency_ms, 1),
                "cost_usd": estimated_cost,
                "ghost_citations": or_ghost,
            }
            db.add(
                models.ReportEntry(
                    session_id=None,
                    mode="grounding_lab",
                    query=payload.query,
                    report_text=raw["text"],
                    sources_json="[]",
                    ghost_citations_json="{}",
                    search_mode="openrouter_web",
                    synth_mode="openrouter",
                    cost_usd=estimated_cost,
                    latency_ms=or_latency_ms,
                )
            )
        except Exception as exc:  # noqa: BLE001 — surfaced to the user, not silently dropped
            openrouter_error = str(exc)

    db.add(own_entry)
    db.commit()
    log_action(db, user, "grounding_lab.compare", model_used="both", detail=f"query={payload.query[:80]}")

    return {
        "own_pipeline": {
            "text": own_answer,
            "sources": gathered["sources"],
            "search_mode": gathered["search_mode"],
            "latency_ms": round(own_latency_ms, 1),
            "cost_usd": 0.0,
            "ghost_citations": own_ghost,
        },
        "openrouter_web_search": openrouter_arm,
        "openrouter_error": openrouter_error,
        "budget": {"daily_limit_usd": budget, "spent_today_usd": round(spent_today, 4)},
    }
