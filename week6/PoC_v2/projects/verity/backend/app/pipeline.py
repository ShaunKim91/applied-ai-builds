"""Shared retrieval + prompt-construction logic used by both the claims
Research/Precedent-Brief path (fictional jurisdiction corpus) and the
Vendor Adoption Radar path (real live web search) — one grounding
discipline, two different, deliberately separated source pools (see
search/jurisdictions.py's module docstring for why)."""
import json

from .search import jurisdictions, rerank_pipeline, web_search


def gather_claims_sources(query: str, jurisdiction: str | None, top_k: int = 5) -> list[dict]:
    raw = jurisdictions.search(query, jurisdiction=jurisdiction, top_k=top_k * 2)
    return rerank_pipeline.rerank_results(query, raw, use_cross_encoder=True, top_k=top_k)


def gather_radar_sources(query: str, top_k: int = 5) -> list[dict]:
    raw = web_search.search(query, max_results=top_k * 2)
    return rerank_pipeline.rerank_results(query, raw, use_cross_encoder=True, top_k=top_k)


def build_context_block(sources: list[dict]) -> str:
    lines = []
    for i, s in enumerate(sources, start=1):
        lines.append(f"[{i}] {s.get('title', '')}\nURL: {s.get('href', '')}\n{s.get('body', '')}")
    return "\n\n".join(lines)


def classify_source_trust(source: dict) -> str:
    """Primary regulatory/case-law (statutes./cases./doi. fictional domains)
    vs. secondary trade/event reporting (catreports.) vs. unverified general
    web (anything from a real live web-search result, i.e. Radar mode)."""
    href = source.get("href", "")
    if any(marker in href for marker in ("statutes.fenwick-demo", "cases.fenwick-demo", "doi.fenwick-demo")):
        return "primary"
    if "catreports.fenwick-demo" in href:
        return "secondary"
    return "unverified"


def extract_first_json_object(text: str) -> dict | None:
    """Brace-depth-counting JSON extraction — the same fix the old Compass
    PoC's debug/issue-01 required after a greedy `\\{.*\\}` regex swallowed a
    real small-model output's stray trailing brace. Applied here from the
    start rather than reintroducing the same bug."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None
