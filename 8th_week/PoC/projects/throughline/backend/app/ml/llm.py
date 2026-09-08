"""Model routing / cloud escalation — a well-known "2025-2026 trend."
When a case needs a second opinion beyond the local 0.5B model (a
complicated multi-policy question, a nuanced escalation summary for a
supervisor), hand the case's redacted rolling summary + recent turns to
OpenRouter's larger qwen3-8b for one best-effort synthesis — never a second
independent tool-calling or memory-writing path. Same real security
invariant as Threshold's own escalation path: this call has no tool access
and cannot itself execute `flag_for_escalation` or anything else; any real
action still flows back through the local orchestrator.

**The one place content actually leaves this container** — so this is
also the second, equally load-bearing call site (besides persistence) for
`ml/redaction.py`'s redaction pass, per architecture.md's explicit PII
boundary: `escalate_to_cloud()` redacts its OWN input immediately before
building the request body, not relying on the caller to have already done
so.
"""
import httpx

from ..config import read_key_file, settings
from .redaction import redact

ESCALATION_SYSTEM_PROMPT = (
    "You are a senior Policyholder Services lead reviewing a colleague's in-progress case. "
    "Given the case summary and recent turns, give one best-effort synthesis or answer. You have no "
    "tools and cannot look anything up yourself or take any action — only summarize/reason over what "
    "is already provided."
)


def openrouter_available() -> bool:
    return read_key_file(settings.openrouter_api_key_file) is not None


def escalate_to_cloud(question: str, case_context: str) -> dict:
    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError("OpenRouter is not configured (no key file present).")
    redacted_question, _ = redact(question)
    redacted_context, _ = redact(case_context)
    resp = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": ESCALATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {redacted_question}\n\nCase context:\n{redacted_context}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return {"text": text, "model": data.get("model", settings.openrouter_model)}
