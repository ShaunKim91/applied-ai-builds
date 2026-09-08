"""Bi-encoder-first, optional cross-encoder-rerank pipeline — reused
verbatim from the old Compass/Week2/4 PoCs."""
from ..ml import embeddings, reranker


def rerank_results(query: str, results: list[dict], use_cross_encoder: bool = True, top_k: int = 5) -> list[dict]:
    if not results:
        return []
    texts = [f"{r.get('title', '')} {r.get('body', '')}" for r in results]
    query_vec = embeddings.embed_query(query)
    doc_vecs = embeddings.embed_passages(texts)

    import numpy as np

    q = np.array(query_vec)
    for i, r in enumerate(results):
        d = np.array(doc_vecs[i])
        denom = (np.linalg.norm(q) * np.linalg.norm(d)) or 1e-9
        r["bi_score"] = float(np.dot(q, d) / denom)

    if use_cross_encoder:
        cross_scores = reranker.rerank(query, texts)
        for r, score in zip(results, cross_scores):
            r["rerank_score"] = score
        results.sort(key=lambda r: r["rerank_score"], reverse=True)
    else:
        results.sort(key=lambda r: r["bi_score"], reverse=True)

    return results[:top_k]
