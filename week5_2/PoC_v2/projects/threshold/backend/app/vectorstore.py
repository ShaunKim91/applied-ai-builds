"""Chroma PersistentClient wrapper — the vector-DB half of this project's
required SQL + Vector DB pairing. Indexes every finished agent run so
History's semantic search works; the SQL rows in `agent_runs` remain the
system of record."""
import chromadb

from .config import settings

_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
_collection = _client.get_or_create_collection("threshold_runs")


def upsert(doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
    _collection.upsert(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[metadata])


def query(embedding: list[float], n_results: int = 5, where: dict | None = None) -> dict:
    return _collection.query(query_embeddings=[embedding], n_results=n_results, where=where)


def count() -> int:
    return _collection.count()
