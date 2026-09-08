"""Bi-encoder + cross-encoder reranking of a fresh batch of live web-search
results. Unlike Week4's Lucent (which queried a pre-indexed VectorDB of
fixed document chunks), this week's source is the live web — there is
nothing to pre-index, so scoring runs directly, at request time, over
whatever the current query's `web_search.search()` call just returned.

This is also, independently, the same reranking mechanism a typical
baseline implementation of this pattern uses for real in production
(bi-encoder cosine `bi_score` + cross-encoder `rerank_score`) — a
hash-based toy embedding is sometimes taught as an introductory stand-in
instead, but never used by real shipped code. We follow the real,
production-grade approach here, same judgment call Week4 made about e5
vs. a stale introductory mock.
"""
from ..ml import embeddings, reranker


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb + 1e-9)


def rerank_results(query: str, results: list[dict], top_k: int, use_rerank: bool = True) -> list[dict]:
    if not results:
        return []

    texts = [f"{r['title']}. {r['body']}" for r in results]
    query_vec = embeddings.embed_query(query)
    passage_vecs = embeddings.embed_passages(texts)
    for r, vec in zip(results, passage_vecs):
        r["bi_score"] = round(_cosine(query_vec, vec), 4)
    results = sorted(results, key=lambda r: r["bi_score"], reverse=True)

    if use_rerank:
        scores = reranker.rerank(query, texts)
        for r, s in zip(results, scores):
            r["rerank_score"] = round(s, 4)
        results = sorted(results, key=lambda r: r["rerank_score"], reverse=True)

    return results[:top_k]
