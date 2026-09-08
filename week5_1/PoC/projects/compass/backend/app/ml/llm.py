"""Model 3 & 4 — the research report's answer-generation brain, with real
token-by-token streaming (Week4's flagship streaming infrastructure,
reused verbatim for the local + plain-OpenRouter paths).

Local Qwen2.5-0.5B-Instruct is the default, no-key-required path. OpenRouter
is a strictly opt-in, user-toggled upgrade, used two distinct ways in this
build: (1) `stream_generate(provider="openrouter")` — an ordinary chat
completion synthesizing a report from sources Compass already retrieved
itself (same mechanism as Week4's Lucent); (2) `openrouter_web_search()` —
OpenRouter's OWN fully-managed web-search plugin, a single request that
performs live web search AND generation together server-side. Both reuse
the one already-validated OpenRouter key; no second cloud vendor is
introduced. OpenAI/Anthropic/Gemini remain scaffolded, not validated.

A typical baseline implementation of this pattern instead defaults to a
rule-based template with no generation at all (`_rule_based_report()`),
offering Gemini or a `claude`/`codex` CLI subprocess call as opt-in extras
— we have neither a Gemini key nor a validated CLI-subprocess mechanism
this round, so OpenRouter fills the "smarter, opt-in" role instead, per
this project's standing "OpenRouter is the only validated cloud API" rule.
"""
import threading

from ..config import read_key_file, settings

_local_lock = threading.Lock()
_local_model = None
_local_tokenizer = None


def _load_local():
    global _local_model, _local_tokenizer
    if _local_model is None:
        with _local_lock:
            if _local_model is None:
                from transformers import AutoModelForCausalLM, AutoTokenizer

                _local_tokenizer = AutoTokenizer.from_pretrained(settings.local_llm_model)
                _local_model = AutoModelForCausalLM.from_pretrained(settings.local_llm_model)
                _local_model.eval()
    return _local_tokenizer, _local_model


def _stream_local(system: str, user: str, max_new_tokens: int = 500):
    """Yields text incrementally as the local model generates it, using
    transformers' TextIteratorStreamer running in a background thread —
    see Week4 PoC's debug/ for the FastAPI + StreamingResponse gotcha this
    pattern is built around (a Depends()-injected DB session closes before
    the generator body finishes; any post-stream write needs a fresh one)."""
    import torch
    from transformers import TextIteratorStreamer

    tokenizer, model = _load_local()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        repetition_penalty=1.15,
        pad_token_id=tokenizer.eos_token_id,
    )

    def _run():
        with torch.no_grad():
            model.generate(**generation_kwargs)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    for new_text in streamer:
        if new_text:
            yield new_text
    thread.join()


def _stream_openrouter(system: str, user: str, max_new_tokens: int = 500):
    """OpenAI-compatible SSE: `data: {...}` lines carrying
    `choices[0].delta.content`, terminated by a literal `data: [DONE]`."""
    import json

    import httpx

    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError("OpenRouter API key file not found or empty: " + settings.openrouter_api_key_file)

    with httpx.stream(
        "POST",
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_new_tokens,
            "temperature": 0.2,
            "stream": True,
        },
        timeout=60.0,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[len("data: ") :]
            if payload.strip() == "[DONE]":
                break
            try:
                event = json.loads(payload)
                delta = event["choices"][0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


def _generate_unavailable(provider: str):
    raise NotImplementedError(
        f"'{provider}' provider is scaffolded (config/env-var ready) but not validated in this build. "
        f"Only 'local' and 'openrouter' were tested this round."
    )


def stream_generate(system: str, user: str, provider: str | None = None, max_new_tokens: int = 500):
    provider = provider or settings.llm_provider
    if provider == "local":
        yield from _stream_local(system, user, max_new_tokens)
    elif provider == "openrouter":
        yield from _stream_openrouter(system, user, max_new_tokens)
    elif provider in ("openai", "anthropic", "gemini"):
        _generate_unavailable(provider)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def openrouter_web_search(query: str, system: str, max_results: int | None = None) -> dict:
    """OpenRouter's fully-managed web-search plugin (explicit form, per
    openrouter.ai/docs/guides/features/plugins/web-search, verified live
    during planning): passing `plugins: [{"id": "web"}]` alongside an
    ordinary chat-completions request makes OpenRouter itself perform live
    web search and fold the results into the response, returning real
    source citations as `annotations[].url_citation`. One request does both
    retrieval and generation server-side — the comparison arm the Grounding
    Lab pits against Compass's own ddgs-based pipeline. Non-streaming: this
    is a lower-volume, deliberately-opt-in comparison call, not the main
    report-generation path.
    """
    import httpx

    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError("OpenRouter API key file not found or empty: " + settings.openrouter_api_key_file)

    resp = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            "max_tokens": 500,
            "temperature": 0.2,
            "plugins": [{"id": "web", "max_results": max_results or settings.web_search_max_results}],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    message = data["choices"][0]["message"]
    text = (message.get("content") or "").strip()
    annotations = message.get("annotations") or []
    citations = [
        {
            "url": a["url_citation"]["url"],
            "title": a["url_citation"].get("title", ""),
            "content": a["url_citation"].get("content", ""),
        }
        for a in annotations
        if a.get("type") == "url_citation" and "url_citation" in a
    ]
    return {"text": text, "citations": citations}


def local_model_info() -> dict:
    tokenizer, model = _load_local()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.local_llm_model, "params": n_params, "loaded": True}


def openrouter_available() -> bool:
    return bool(read_key_file(settings.openrouter_api_key_file))
