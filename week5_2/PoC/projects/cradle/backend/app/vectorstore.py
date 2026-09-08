"""Vector store wrapper — indexes past agent runs (question + final answer)
so the History page's semantic search actually works.

Primary backend: Chroma, via `PersistentClient` (survives container
restarts). A typical baseline implementation of this pattern has **no
vector store or persistence at all** — every agent run is stateless/
in-memory (a fresh Streamlit button click each time), so there is nothing
to compare this against there; the nearest real precedent is the
Week4/5_1 PoCs' `PersistentClient` usage, reused verbatim here. Falls
back automatically to a pure-Python cosine-similarity list if chromadb
fails to import/initialize, so archive search never hard-fails.
"""
import math
import threading

from .config import settings

_lock = threading.Lock()
_collection = None  # Chroma collection, or False to mean "fallback mode"
_fallback_store: list[tuple[str, str, list[float], dict]] = []


def _get_collection():
    global _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                try:
                    import chromadb

                    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
                    _collection = client.get_or_create_collection(
                        name="chunks", metadata={"hnsw:space": "cosine"}
                    )
                except Exception:
                    _collection = False
    return _collection


def upsert(item_id: str, text: str, vector: list[float], metadata: dict) -> None:
    collection = _get_collection()
    if collection:
        collection.upsert(ids=[item_id], embeddings=[vector], documents=[text], metadatas=[metadata])
    else:
        _fallback_store[:] = [row for row in _fallback_store if row[0] != item_id]
        _fallback_store.append((item_id, text, vector, metadata))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


def query(vector: list[float], top_k: int = 5) -> list[dict]:
    collection = _get_collection()
    if collection:
        result = collection.query(query_embeddings=[vector], n_results=top_k)
        if not result["ids"] or not result["ids"][0]:
            return []
        out = []
        for i, d, m, dist in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            out.append({"id": i, "text": d, "metadata": m, "similarity": round(1 - dist, 4)})
        return out

    scored = sorted(
        ((row[0], row[1], row[3], _cosine(vector, row[2])) for row in _fallback_store),
        key=lambda r: r[3],
        reverse=True,
    )[:top_k]
    return [{"id": i, "text": t, "metadata": m, "similarity": round(s, 4)} for i, t, m, s in scored]


def backend_name() -> str:
    return "chromadb" if _get_collection() else "fallback-cosine"
