"""Chroma PersistentClient wrapper — the vector-DB half of this project's
required SQL + Vector DB pairing. Indexes each case's rolling summary (post-
redaction) so the Cases directory's "has this caller called before about
something similar" semantic search works; the SQL rows in `caller_cases` /
`conversation_turns` remain the system of record."""
import chromadb

from .config import settings

_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
_collection = _client.get_or_create_collection("throughline_cases")


def upsert(doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
    _collection.upsert(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[metadata])


def query(embedding: list[float], n_results: int = 5, where: dict | None = None) -> dict:
    return _collection.query(query_embeddings=[embedding], n_results=n_results, where=where)


def delete(doc_id: str) -> None:
    """Used by the purge/right-to-erasure flow — see chains/orchestrator.py
    `purge_case()`. Best-effort: a missing id is not an error."""
    try:
        _collection.delete(ids=[doc_id])
    except Exception:
        pass


def count() -> int:
    return _collection.count()
