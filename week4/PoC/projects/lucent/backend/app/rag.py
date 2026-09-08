"""Shared retrieval logic — the retrieve(-then-rerank) pipeline both the
Chat and Retrieval Lab routers call, so the two pages can never silently
drift out of sync on how retrieval actually works.
"""
from . import vectorstore
from .config import settings
from .ml import embeddings, reranker


def retrieve(query: str, top_k: int | None = None, use_rerank: bool = False) -> list[dict]:
    top_k = top_k or settings.retrieval_top_k
    query_vector = embeddings.embed_query(query)
    over_fetch = top_k * 3 if use_rerank else top_k
    candidates = vectorstore.query(query_vector, top_k=over_fetch)

    if not use_rerank or not candidates:
        return candidates[:top_k]

    scores = reranker.rerank(query, [c["text"] for c in candidates])
    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)
    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]


def build_context_block(sources: list[dict]) -> str:
    """Formats retrieved chunks as a numbered context block for the LLM
    prompt — the numbering here is exactly what `[n]` citations in the
    generated answer refer back to, and what groundedness.check_citations
    validates against."""
    lines = []
    for i, s in enumerate(sources, start=1):
        title = s["metadata"].get("title", "source")
        lines.append(f"[{i}] ({title}) {s['text']}")
    return "\n\n".join(lines)


RAG_SYSTEM_PROMPT = (
    "You are a careful research assistant. Answer the user's question using "
    "ONLY the numbered sources below. Cite every claim with the matching "
    "[n] marker. If the sources don't contain the answer, say you don't "
    "know rather than guessing. Keep the answer concise (3-6 sentences)."
)
