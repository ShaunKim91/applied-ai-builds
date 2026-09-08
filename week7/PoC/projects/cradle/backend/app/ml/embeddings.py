"""Model 1 — bi-encoder embeddings for the agent-run archive's semantic search.

intfloat/multilingual-e5-small: the same embedding model validated in the
Week4/6 PoCs — reused here for its multilingual coverage (100+
languages sharing one embedding space), which
Cradle relies on for embedding past agent runs (question + final answer)
so the History page's semantic search works in either language.

E5 models require a task-specific text prefix per their model card — this
is not optional formatting, it measurably changes retrieval quality:
"query: " for search queries, "passage: " for the documents being indexed.
Forgetting this is a common, real mistake when adopting e5 models; this
module bakes the correct prefix in so callers never have to remember it.
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


def embed_query(text: str) -> list[float]:
    return _embed_one(f"query: {text}")


def embed_passage(text: str) -> list[float]:
    return _embed_one(f"passage: {text}")


def embed_passages(texts: list[str]) -> list[list[float]]:
    model = _load()
    prefixed = [f"passage: {t}" for t in texts]
    vectors = model.encode(prefixed, normalize_embeddings=True).tolist()
    return vectors


def _embed_one(prefixed_text: str) -> list[float]:
    model = _load()
    return model.encode([prefixed_text], normalize_embeddings=True).tolist()[0]


def dimension() -> int:
    model = _load()
    return model.get_sentence_embedding_dimension()


def model_info() -> dict:
    return {"model_id": settings.embedding_model, "dimension": dimension(), "loaded": True}
