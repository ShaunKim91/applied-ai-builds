"""Model 2 / 6 — Cross-encoder reranker for the second ("precision") stage
of Knowledge Search.

cross-encoder/ms-marco-MiniLM-L-6-v2: jointly encodes (query, document)
pairs — slower than the bi-encoder (can't be pre-computed, must run at query
time) but measurably more accurate, exactly the kind of trade-off a simple
"환불" (refund) vs "날씨" (weather) example is often used to demonstrate.
This module is what lets Knowledge Search show a real before/after
comparison instead of just asserting reranking helps.
"""
import threading

from ..config import settings

_lock = threading.Lock()
_model = None


def _load():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(settings.reranker_model)
    return _model


def rerank(query: str, documents: list[str]) -> list[float]:
    """Returns one relevance score per document, same order as `documents`
    (higher = more relevant; NOT a probability, just a comparable score)."""
    if not documents:
        return []
    model = _load()
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs)
    return [float(s) for s in scores]


def model_info() -> dict:
    _load()
    return {"model_id": settings.reranker_model, "loaded": True}
