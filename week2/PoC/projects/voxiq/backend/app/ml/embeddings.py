"""Model 1 / 6 — Bi-encoder embeddings for the first-pass ("retrieve") stage
of Knowledge Search.

sentence-transformers/all-MiniLM-L6-v2: a small, fast, CPU-friendly bi-encoder
that is a common first choice for this kind of retrieval task. Encodes
each document independently (fast, pre-computable), which is exactly why a
second cross-encoder pass (see reranker.py) is needed for precision.
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
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed(texts: list[str] | str) -> list[float] | list[list[float]]:
    model = _load()
    single = isinstance(texts, str)
    values = [texts] if single else texts
    vectors = model.encode(values, normalize_embeddings=True).tolist()
    return vectors[0] if single else vectors


def dimension() -> int:
    model = _load()
    return model.get_sentence_embedding_dimension()


def model_info() -> dict:
    return {"model_id": settings.embedding_model, "dimension": dimension(), "loaded": True}
