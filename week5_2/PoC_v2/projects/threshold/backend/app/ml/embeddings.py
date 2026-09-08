"""Lazy-loaded singleton wrapper around `intfloat/multilingual-e5-small`.

e5 models require a task-specific text prefix per their model card
("query: " vs "passage: ") — reused verbatim from every prior PoC in this
project series that uses this same model.
"""
import threading

from sentence_transformers import SentenceTransformer

from ..config import settings

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(settings.embedding_model)
    return _model


def dimension() -> int:
    return _get_model().get_sentence_embedding_dimension()


def embed_query(text: str) -> list[float]:
    return _get_model().encode(f"query: {text}", normalize_embeddings=True).tolist()


def embed_passage(text: str) -> list[float]:
    return _get_model().encode(f"passage: {text}", normalize_embeddings=True).tolist()


def embed_passages(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {t}" for t in texts]
    return _get_model().encode(prefixed, normalize_embeddings=True).tolist()
