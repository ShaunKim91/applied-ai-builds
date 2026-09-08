"""Model 3 / 5 — Multilingual sentence embeddings for semantic catalog search.

intfloat/multilingual-e5-small: 384-dim, CPU-friendly, and a well-regarded
choice for Korean-language retrieval quality, as encouraged by the project
brief.

E5 models are trained with an asymmetric "query: " / "passage: " prefix
convention — using the right prefix measurably improves retrieval quality,
so embed_query/embed_passage apply it automatically.
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


def _embed(texts: list[str]) -> list[list[float]]:
    model = _load()
    return model.encode(texts, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return _embed([f"query: {text}"])[0]


def embed_passage(text: str) -> list[float]:
    return _embed([f"passage: {text}"])[0]


def dimension() -> int:
    model = _load()
    return model.get_sentence_embedding_dimension()


def model_info() -> dict:
    return {"model_id": settings.embedding_model, "dimension": dimension(), "loaded": True}
