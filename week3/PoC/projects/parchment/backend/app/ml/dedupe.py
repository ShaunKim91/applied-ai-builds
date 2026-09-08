"""Near-duplicate document detection — embeds every processed document
(receipt / PDF / HTML table) with all-MiniLM-L6-v2 and checks it against
everything already in the Chroma vector store.

This is a genuinely different use case from retrieval-augmented generation
(RAG): it never feeds retrieved text back into an LLM to answer a
question, and there is no "search" UI over the document corpus — it's a
single similarity check that runs automatically after processing, purely
to flag re-submitted/duplicate documents (a real back-office concern, e.g.
catching a receipt submitted twice for reimbursement). This narrow scope
is deliberate: full semantic search/RAG over documents (embeddings +
ChromaDB + retrieve-then-answer) is a substantial feature of its own, and
this PoC is scoped to avoid quietly growing into a second, half-built
product — see architecture.md.
"""
from . import embeddings
from .. import vectorstore
from ..config import settings


def register_and_check(doc_id: str, doc_type: str, text: str, metadata: dict) -> dict:
    """Embeds `text`, checks it against the existing store for a near-duplicate,
    then upserts it (so future documents can be compared against this one
    too). Returns {"is_duplicate": bool, "duplicate_of": id|None, "similarity": float}."""
    if not text or not text.strip():
        return {"is_duplicate": False, "duplicate_of": None, "similarity": 0.0}

    vector = embeddings.embed(text)
    # top_k=8, then filtered down to same-doc_type candidates below — a
    # small over-fetch so a receipt near-duplicate isn't crowded out of a
    # small top_k by unrelated PDF entries ranked slightly higher.
    candidates = vectorstore.query(vector, top_k=8)

    best = None
    for c in candidates:
        if c["id"] == doc_id:
            continue
        if c["metadata"].get("doc_type") != doc_type:
            continue  # only compare within the same document type
        if best is None or c["similarity"] > best["similarity"]:
            best = c

    vectorstore.upsert(doc_id, text, vector, {"doc_type": doc_type, **metadata})

    if best and best["similarity"] >= settings.dedupe_similarity_threshold:
        return {
            "is_duplicate": True,
            "duplicate_of": best["id"],
            "similarity": best["similarity"],
        }
    return {
        "is_duplicate": False,
        "duplicate_of": None,
        "similarity": best["similarity"] if best else 0.0,
    }
