import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.fomc_minutes import chunk_text, ensure_fomc_minutes
from ..ml import embeddings as emb_ml
from ..ml import reranker as rerank_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/search", tags=["search"])


def index_fomc_minutes() -> dict:
    """Idempotent: chunks + embeds + upserts FOMC minutes into the vector
    store. Safe to call repeatedly — upsert overwrites the same chunk IDs
    rather than duplicating them."""
    docs = ensure_fomc_minutes(settings.data_dir)
    total_chunks = 0
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"fomc-{doc['date']}-{i}"
            vector = emb_ml.embed(chunk)
            vectorstore.upsert(chunk_id, chunk, vector, {"source": "fomc", "date": doc["date"], "chunk": i})
            total_chunks += 1
    return {"documents": len(docs), "chunks_indexed": total_chunks}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=300)
    top_k: int = Field(5, ge=1, le=20)


@router.get("/status")
def status(user: models.User = Depends(get_current_user)):
    return {"backend": vectorstore.backend_name()}


@router.post("")
def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    with timed() as elapsed:
        query_vector = emb_ml.embed(payload.query)
        # Over-fetch candidates for the bi-encoder ("retrieve") stage so the
        # cross-encoder ("rerank") stage has a real pool to work with —
        # the standard retrieve-then-rerank two-stage architecture.
        candidates = vectorstore.query(query_vector, top_k=max(payload.top_k * 3, 10))
        bi_ranked = candidates[: payload.top_k]

        cross_ranked = []
        if candidates:
            docs = [c["text"] for c in candidates]
            scores = rerank_ml.rerank(payload.query, docs)
            reranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
            cross_ranked = [{**c, "rerank_score": round(s, 4)} for c, s in reranked[: payload.top_k]]
    latency = elapsed()

    top1_changed = bool(
        bi_ranked and cross_ranked and bi_ranked[0]["id"] != cross_ranked[0]["id"]
    )

    record = models.SearchQuery(
        owner_id=user.id,
        query_text=payload.query,
        bi_results_json=json.dumps(bi_ranked),
        cross_results_json=json.dumps(cross_ranked),
        top1_changed=top1_changed,
        latency_ms=latency,
    )
    db.add(record)
    db.commit()

    log_action(
        db, user, "search.knowledge",
        model_used=f"{settings.embedding_model} + {settings.reranker_model}",
        detail=payload.query, latency_ms=latency,
    )

    return {
        "bi_encoder_results": bi_ranked,
        "cross_encoder_results": cross_ranked,
        "top1_changed": top1_changed,
        "backend": vectorstore.backend_name(),
        "latency_ms": round(latency, 1),
    }
