"""Live web search — the default (free, no API key) retrieval source.

Uses `ddgs` (PyPI, formerly `duckduckgo-search`; confirmed live during
planning: `pip install ddgs`, `DDGS().text(query, max_results=n)` ->
[{title, href, body}, ...], no key required). ddgs's own docs disclose it's
an unofficial client scraping DuckDuckGo's own search results ("for
educational purposes"), so a runtime failure (rate limit, network block,
layout change) is a real, expected possibility — not a hypothetical one.

This module handles that with a standard mock-first resilience pattern:
mock-first, with a deliberate, clearly-labeled fallback rather than a bare
500 error. The one difference from a typical introductory version of this
pattern is that the fallback here is reported honestly to the caller
(`source: "mock"` on every result) instead of being silently
indistinguishable from a real result — see routers/research.py, which
surfaces this in the report's metadata so a user never mistakes a mock
result for a real citation.
"""
import logging

from ..config import settings

logger = logging.getLogger("compass")


def _mock_results(query: str, max_results: int) -> list[dict]:
    return [
        {
            "title": f"[Mock] {query} — reference {i + 1}",
            "href": f"https://example.invalid/mock-search/{i + 1}",
            "body": (
                f"Live web search was unavailable, so this is a deterministic placeholder "
                f"result for the query '{query}'. It exists so the research pipeline can "
                f"still be demonstrated end-to-end; it is never presented as a real citation."
            ),
            "source": "mock",
        }
        for i in range(max_results)
    ]


def _ddgs_results(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    raw = DDGS().text(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "href": r.get("href", ""),
            "body": r.get("body", ""),
            "source": "ddgs",
        }
        for r in raw
        if r.get("href")
    ]


def search(query: str, max_results: int | None = None) -> dict:
    """Returns {"results": [...], "mode": "ddgs" | "mock", "error": str | None}."""
    max_results = max_results or settings.web_search_max_results
    try:
        results = _ddgs_results(query, max_results)
        if not results:
            raise RuntimeError("ddgs returned zero results")
        return {"results": results, "mode": "ddgs", "error": None}
    except Exception as exc:  # noqa: BLE001 — any failure mode falls back the same way
        logger.warning("Live web search failed (%s) — falling back to mock results.", exc)
        return {"results": _mock_results(query, max_results), "mode": "mock", "error": str(exc)}


def connectivity_check() -> dict:
    """Used by the bootstrap warm-step and /api/health/ready — a cheap real
    search so operators know at a glance whether ddgs is actually reachable
    from inside this container, without waiting for a user's first query to
    find out."""
    result = search("compass connectivity check", max_results=1)
    return {"mode": result["mode"], "ok": result["mode"] == "ddgs"}
