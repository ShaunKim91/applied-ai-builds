"""Lazy-loaded singleton wrapper around `cross-encoder/ms-marco-MiniLM-L-6-v2`
— reused verbatim from the Week2/13/14_1(old) PoCs, and independently the
same reranker a typical first-pass implementation of this search-plus-rerank
pattern tends to reach for."""
import threading

from sentence_transformers import CrossEncoder

from ..config import settings

_model: CrossEncoder | None = None
_lock = threading.Lock()


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = CrossEncoder(settings.reranker_model)
    return _model


def rerank(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    pairs = [(query, doc) for doc in documents]
    scores = _get_model().predict(pairs)
    return [float(s) for s in scores]
