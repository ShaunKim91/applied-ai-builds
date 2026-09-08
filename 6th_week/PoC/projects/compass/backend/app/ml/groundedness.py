"""Groundedness verification — this project's generalization of the "no
hallucination" discipline every prior PoC in this series has enforced in a
feature-specific way (Week3's numeric cross-check compared summary numbers
against source text; this applies the same idea to a full RAG answer).

Two independent checks, both required to pass for a "grounded" verdict:

1. **Structural** — every `[n]` citation marker the answer contains must
   refer to a source index that was actually provided in the prompt. A
   model inventing `[7]` when only 4 sources existed is a real, catchable
   failure mode, and catching it needs no AI model at all — just parsing.
2. **Content** — split the answer into sentences, embed each one
   (`ml/embeddings.py`, reused — same model that embedded the sources), and
   require every sentence's cosine similarity to at least one retrieved
   chunk to clear `settings.groundedness_similarity_threshold`. A sentence
   that doesn't resemble anything retrieved is a real sign the model added
   something not actually in the sources, even if it didn't cite a bad
   index.
"""
import re

from . import embeddings
from ..config import settings

_CITATION_RE = re.compile(r"\[(\d+)\]")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+")


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb + 1e-9)


def check_citations(answer: str, source_count: int) -> dict:
    cited = {int(n) for n in _CITATION_RE.findall(answer)}
    invalid = sorted(n for n in cited if n < 1 or n > source_count)
    return {"passed": len(invalid) == 0, "cited": sorted(cited), "invalid": invalid}


def check_content(answer: str, source_texts: list[str]) -> dict:
    """Returns per-sentence groundedness and an overall score in [0, 1]."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(answer) if s.strip()]
    if not sentences or not source_texts:
        return {"passed": True, "score": 1.0, "sentences": []}

    source_vectors = [embeddings.embed_passage(t) for t in source_texts]
    results = []
    grounded_count = 0
    for sentence in sentences:
        vec = embeddings.embed_query(sentence)
        best = max((_cosine(vec, sv) for sv in source_vectors), default=0.0)
        is_grounded = best >= settings.groundedness_similarity_threshold
        grounded_count += int(is_grounded)
        results.append({"sentence": sentence, "similarity": round(best, 3), "grounded": is_grounded})

    score = grounded_count / len(sentences)
    return {"passed": score >= 0.8, "score": round(score, 3), "sentences": results}


def verify(answer: str, source_texts: list[str]) -> dict:
    citation_check = check_citations(answer, len(source_texts))
    content_check = check_content(answer, source_texts)
    return {
        "passed": citation_check["passed"] and content_check["passed"],
        "citation_check": citation_check,
        "content_check": content_check,
    }
