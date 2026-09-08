"""Ghost-citation detection — a verification technique commonly taught as
an introductory exercise (regex-extract every URL the model's answer
cites, diff against the URLs actually present in the retrieved search
results) but that a typical baseline implementation of this pattern never
implements as a real feature. Compass surfaces it directly: any URL the
model names that was
never actually retrieved is flagged as a "ghost citation" — a strong signal
the model paraphrased a URL from its own training data (or invented one
outright) instead of grounding strictly in what was searched.

This is a distinct verification axis from ml/groundedness.py's [n]-marker
structural check and sentence-similarity content check (both reused
verbatim from Week4) — that check catches an invalid *index* or an
ungrounded *sentence*; this one catches an invalid *URL*, the citation unit
that matters specifically for web-search grounding.
"""
import re

_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")


def _normalize(url: str) -> str:
    """Strips a trailing sentence-punctuation character a regex match can
    accidentally swallow (e.g. "...report.[1] (https://x.com/a)." ->
    trailing '.'), and a trailing slash, so a citation and its source URL
    compare equal even with minor surface differences."""
    return url.rstrip(".,;:)]}\"'").rstrip("/")


def extract_cited_urls(answer: str) -> list[str]:
    return [_normalize(u) for u in _URL_RE.findall(answer)]


def check(answer: str, retrieved_urls: list[str]) -> dict:
    """Returns which cited URLs are real (matched an actually-retrieved
    source) vs. ghosts (cited but never retrieved)."""
    cited = extract_cited_urls(answer)
    retrieved_set = {_normalize(u) for u in retrieved_urls}
    ghosts = sorted({u for u in cited if u not in retrieved_set})
    real = sorted({u for u in cited if u in retrieved_set})
    return {
        "passed": len(ghosts) == 0,
        "cited_count": len(set(cited)),
        "real_citations": real,
        "ghost_citations": ghosts,
    }
