"""Shared research pipeline plumbing — the search-then-rerank step and
prompt construction both the Research and Trend Radar routers call, so the
two features can never silently drift on how grounding actually works (same
reasoning as Week4 Lucent's rag.py).
"""
import json
import re

from .config import settings
from .search import rerank_pipeline, web_search


def gather_sources(query: str, use_rerank: bool = True, top_k: int | None = None) -> dict:
    top_k = top_k or settings.web_search_rerank_top_k
    found = web_search.search(query)
    ranked = rerank_pipeline.rerank_results(query, found["results"], top_k=top_k, use_rerank=use_rerank)
    return {"sources": ranked, "search_mode": found["mode"], "search_error": found["error"]}


def build_context_block(sources: list[dict]) -> str:
    lines = []
    for i, s in enumerate(sources, start=1):
        lines.append(f"[{i}] {s['title']} ({s['href']})\n{s['body']}")
    return "\n\n".join(lines)


# The 4-part grounding prompt (role / input scope / output format /
# verification rule) is a common structure for grounded-generation prompts,
# adapted to English for reliability with the small local model — same
# reasoning Week4 used for its own RAG_SYSTEM_PROMPT. The "write the URL
# verbatim" instruction exists specifically so ml/ghost_citation.py's check
# is meaningful: a model that paraphrases/invents a URL instead of copying
# one of the given ones will visibly fail that check, exactly what it
# exists to catch (see ghost_citation.py's own module docstring).
RESEARCH_SYSTEM_PROMPT = (
    "You are a careful research analyst. Answer the user's question using ONLY the "
    "numbered web search results below. Cite every claim with the matching [n] marker. "
    "End your answer with a final line starting 'Sources:' listing the exact URL(s) you "
    "actually relied on, copied verbatim from the numbered results above — never write a "
    "URL that is not one of the ones given. If the search results don't answer the "
    "question, say so rather than guessing. Keep the answer concise (3-6 sentences)."
)

# A 3-lens tool-evaluation framework (cost / security / approval friction),
# turned into a real, structured feature — a typical baseline implementation
# of this pattern only discusses this kind of framework in a doc, it's
# never implemented as working code there.
RADAR_SYSTEM_PROMPT = (
    "You are evaluating an AI tool or technology trend across three lenses: Cost, "
    "Security, and Approval-friction (how hard it would be to get approved for use inside "
    "a company). Using ONLY the numbered web search results below, rate each lens as "
    "exactly one of \"Low\", \"Medium\", \"High\", or \"Insufficient evidence\" plus one "
    "short justification sentence citing [n] markers. If the sources do not give enough "
    "information for a lens, you MUST answer \"Insufficient evidence\" for it rather than "
    "guessing. Respond with ONLY a single JSON object, no other text, in exactly this "
    'shape: {"cost": {"level": "...", "note": "..."}, "security": {"level": "...", "note": '
    '"..."}, "approval": {"level": "...", "note": "..."}}'
)

def _extract_first_json_object(text: str) -> str | None:
    """Finds the substring spanning the first `{` to ITS matching `}` by
    counting brace depth, instead of a naive greedy regex (`\\{.*\\}`) that
    matches from the first `{` all the way to the LAST `}` in the text.

    That naive form was tried first and failed on real output: the local
    0.5B model occasionally emits a syntactically-complete JSON object
    followed by stray extra closing braces (observed verbatim:
    `..."note": "..."}}}` — one `}` too many). The greedy regex swallowed
    those extra braces into the "match," making `json.loads` fail on
    otherwise-perfectly-valid JSON. Depth-counting stops at the first
    properly-balanced object and ignores anything after it, so this exact
    failure mode no longer causes an honest, fully-correct extraction to be
    thrown away. See debug/issue-01 for the observed case.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_radar_json(text: str) -> dict | None:
    """Best-effort JSON extraction from a small local model's output, which
    may wrap the JSON in prose despite instructions. Returns None (never a
    fabricated result) if no valid, correctly-shaped object can be found —
    the caller must surface that honestly rather than invent a verdict."""
    candidate = _extract_first_json_object(text)
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    required = {"cost", "security", "approval"}
    if not required.issubset(parsed.keys()):
        return None
    for lens in required:
        if not isinstance(parsed[lens], dict) or "level" not in parsed[lens]:
            return None
    return parsed
