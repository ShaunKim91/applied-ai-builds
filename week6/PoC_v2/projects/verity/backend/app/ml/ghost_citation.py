"""Ghost-citation checking — reused from the old Compass PoC's own D3-taught
technique: extract every URL the model actually wrote in its answer, and
flag any that weren't among the retrieved sources. Catches a paraphrased or
invented citation URL that a sentence-similarity check alone might miss —
directly relevant to Verity's "must survive an appeal" narrative, since a
fabricated source in a precedent brief is exactly the failure mode a
compliance reviewer needs caught before it reaches a claim file."""
import re

_URL_RE = re.compile(r"https?://[^\s\)\]\"']+")

# A real, measured gap found during this build: groundedness.py's
# sentence-similarity check (multilingual-e5-small embeddings) gave a
# PERFECT 1.0 score to a Qwen2.5-0.5B precedent-brief answer that named
# "The Federal Insurance Office (FIO)" as governing authority — a real US
# federal body, invented by the model, appearing in NONE of the fictional
# Cedermoor sources it was given. Measured directly: multiple genuinely
# unrelated sentences scored 0.74-0.82 cosine similarity against fraud-
# pattern descriptions that have nothing to do with them (see
# debug/issue-0X in this project's own debug log) — this embedding model's
# similarity scores track topical/domain adjacency, not factual grounding,
# so a hallucinated-but-topically-plausible named authority can slip
# through undetected. This is a real, partial mitigation, not a full fix:
# a simple, deterministic proper-noun-phrase check that flags any
# multi-word Title Case phrase in the answer that doesn't appear verbatim
# in the retrieved source text — catching exactly this failure mode
# without requiring a different (and not available in this project's
# validated model set) fact-verification model.
_ENTITY_RE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,4}\b")
# Never flag the fictional jurisdiction names themselves, or common
# section-label words that happen to be capitalized in the brief template
# (e.g. "Governing Authority" is a label this project itself writes, not a
# model claim) — the ENTITY check is about claims the MODEL introduces.
_ALLOWLIST = {
    "Fenwick Mutual",
    "Ashford",
    "Belmont Bay",
    "Cedermoor",
    "Dunraven",
    "Elmsworth",
    "Fairhaven",
    "Governing Authority",
    "Facts Applied",
    "Final Answer",
}


def check(answer_text: str, source_urls: list[str]) -> dict:
    cited = set(_URL_RE.findall(answer_text))
    real = set(source_urls)
    ghosts = sorted(u.rstrip(".,;:") for u in cited if u.rstrip(".,;:") not in real)
    return {"passed": len(ghosts) == 0, "cited_count": len(cited), "ghost_urls": ghosts}


def check_entities(answer_text: str, source_texts: list[str]) -> dict:
    """Flags multi-word Title Case phrases (a crude but effective proper-
    noun detector) named in the answer that don't appear verbatim anywhere
    in the actual retrieved source text — e.g. a fabricated governing body
    or case name the model introduced on its own."""
    combined = " ".join(source_texts)
    candidates = {m.group(0) for m in _ENTITY_RE.finditer(answer_text)}
    unverified = sorted(c for c in candidates if c not in _ALLOWLIST and c not in combined)
    return {"passed": len(unverified) == 0, "unverified_entities": unverified}
