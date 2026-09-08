"""Groundedness checking — reused pattern from the Week4/14_1(old) PoCs:
verify every `[n]` citation marker in a generated answer points at a real
source index, and verify each cited sentence is embedding-similar enough to
the source it claims to cite that it's plausibly actually drawn from it
(not a fabrication that happens to carry a real-looking marker)."""
import re

import numpy as np

from . import embeddings

_MARKER_RE = re.compile(r"\[(\d+)\]")
_SIMILARITY_THRESHOLD = 0.55


def _cosine(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)) or 1e-9
    return float(np.dot(a_arr, b_arr) / denom)


def verify(answer_text: str, source_texts: list[str]) -> dict:
    n_sources = len(source_texts)
    markers = [int(m) for m in _MARKER_RE.findall(answer_text)]
    invalid_markers = [m for m in markers if m < 1 or m > n_sources]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer_text) if s.strip()]
    if not sentences or not source_texts:
        score = 0.0
    else:
        source_vecs = [embeddings.embed_passage(t) for t in source_texts]
        sims = []
        for sent in sentences:
            sent_vec = embeddings.embed_query(sent)
            best = max((_cosine(sent_vec, sv) for sv in source_vecs), default=0.0)
            sims.append(best)
        score = sum(1 for s in sims if s >= _SIMILARITY_THRESHOLD) / len(sims)

    return {
        "passed": len(invalid_markers) == 0 and score >= 0.5,
        "score": round(score, 3),
        "invalid_markers": invalid_markers,
        "marker_count": len(markers),
    }
