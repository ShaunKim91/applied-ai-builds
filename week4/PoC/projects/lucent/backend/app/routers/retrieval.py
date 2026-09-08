"""Retrieval Lab — the bi- vs. bi+cross-encoder comparison UX validated in
the Week2 PoC's Knowledge Search feature, reused here for RAG specifically
(most introductory material never shows this side-by-side; the same
approach applies just as well to a document-QA corpus as it did to
meeting transcripts)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..rag import retrieve
from ..security import get_current_user

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


class CompareRequest(BaseModel):
    query: str
    top_k: int | None = None


@router.post("/compare")
def compare(payload: CompareRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    with timed() as elapsed:
        bi_results = retrieve(payload.query, top_k=payload.top_k, use_rerank=False)
        cross_results = retrieve(payload.query, top_k=payload.top_k, use_rerank=True)
    latency_ms = elapsed()

    top1_changed = bool(bi_results and cross_results and bi_results[0]["id"] != cross_results[0]["id"])
    log_action(db, user, "retrieval.compare", model_used=settings.reranker_model, latency_ms=latency_ms)

    return {
        "bi_results": bi_results,
        "cross_results": cross_results,
        "top1_changed": top1_changed,
        "latency_ms": round(latency_ms, 1),
    }
