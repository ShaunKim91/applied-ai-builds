"""Model routing — the opt-in escalation to a larger cloud model, a
well-documented "2025-2026 trend" (model-routing cost/quality tradeoffs)
that a typical baseline build discusses but never implements as code.

This is deliberately scoped narrower than a full cloud-side ReAct loop:
given a local run's full trace (it got stuck, hit its step limit, or the
user just wants a second opinion), ask OpenRouter's larger model for one
best-effort final answer synthesizing everything already tried — not a
second independent tool-calling agent. Budget-gated by the same daily-cap
pattern validated in the Week6 "Compass" PoC.
"""
from ..config import read_key_file, settings

ESCALATION_SYSTEM_PROMPT = (
    "You are a more capable AI assistant taking over from a smaller local agent that got stuck. "
    "You will be given the user's original question and the smaller agent's full reasoning trace "
    "(its thoughts, tool calls, and tool results so far). Using ONLY the information already "
    "gathered in that trace, write the best final answer you can. If the trace doesn't contain "
    "enough information to answer, say so honestly rather than guessing."
)


def escalate_to_cloud(question: str, trace_text: str) -> dict:
    import httpx

    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError("OpenRouter API key file not found or empty: " + settings.openrouter_api_key_file)

    user_prompt = f"Original question: {question}\n\nAgent trace so far:\n{trace_text}"
    resp = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": ESCALATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 300,
            "temperature": 0.2,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"text": data["choices"][0]["message"]["content"].strip(), "model": settings.openrouter_model}


def openrouter_available() -> bool:
    return bool(read_key_file(settings.openrouter_api_key_file))
