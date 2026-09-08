"""Live web search — used ONLY by the Vendor & Tool Adoption Radar feature
(evaluating a real AI/InsurTech vendor tool is genuinely real-world
research). Claims/jurisdiction research never uses this module — see
jurisdictions.py's module docstring for why. Same `ddgs` + deterministic
mock-fallback design validated in the old Compass PoC, reused verbatim."""
from ddgs import DDGS

from .. import state

_MOCK_RESULTS = [
    {
        "title": "Evaluating AI vendor tools for insurance claims operations",
        "href": "https://example.org/insurtech-vendor-evaluation-guide",
        "body": "A framework for weighing cost, data-security posture, and approval friction before adopting a third-party AI tool in a regulated claims workflow.",
    },
    {
        "title": "2025-2026 trends in claims automation and model routing",
        "href": "https://example.org/claims-automation-trends-2025",
        "body": "Carriers are increasingly routing routine claims tasks to small local models and escalating only ambiguous cases to larger, costlier cloud models.",
    },
]


def search(query: str, max_results: int = 5) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if results:
            state.set_search_mode("ddgs")
            return [{"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")} for r in results]
    except Exception:
        pass
    state.set_search_mode("mock")
    return _MOCK_RESULTS[:max_results]


def connectivity_check() -> None:
    search("insurance claims AI tools", max_results=1)
