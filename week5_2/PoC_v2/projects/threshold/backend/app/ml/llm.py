"""Model routing / cloud escalation — a common introductory technique for
combining local and cloud models, not carried through in a typical
first-pass build. When the local agent stalls
(step-limit) or a user wants a second opinion, hand its full trace to
OpenRouter's larger qwen3-8b for ONE best-effort final answer — never a
second independent tool-calling loop. This is a real security invariant,
not an implementation detail: the escalation path has zero tool-calling
capability and cannot itself call `issue_claim_payout` — any real payout
must still flow back through the local ReAct loop + guardrail engine."""
import httpx

from ..config import read_key_file, settings

ESCALATION_SYSTEM_PROMPT = (
    "You are a senior claims examiner reviewing a colleague's in-progress "
    "work. Given the original question and the ReAct trace so far, give one "
    "best-effort final answer. You have no tools — you can only synthesize "
    "from what the trace already shows; you cannot look anything up or take "
    "any action yourself."
)


def openrouter_available() -> bool:
    return read_key_file(settings.openrouter_api_key_file) is not None


def escalate_to_cloud(question: str, trace_text: str) -> dict:
    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError("OpenRouter is not configured (no key file present).")
    resp = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": ESCALATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nTrace so far:\n{trace_text}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return {"text": text, "model": data.get("model", settings.openrouter_model)}
