"""Model 3 & 4 — the chat assistant's answer-generation brain, with real
token-by-token streaming (the flagship upgrade this week's brief calls for
over the plain request/response generation used in the Week1-3 PoCs).

Local Qwen2.5-0.5B-Instruct is the default, no-key-required path (same
model validated/reused across the Week1-3 PoCs). OpenRouter's
qwen/qwen3-8b is a strictly opt-in, user-toggled upgrade — validated with a
real key this round. OpenAI/Anthropic/Gemini are scaffolded (config fields
exist in config.py) but NOT validated: calling them raises a clear
NotImplementedError. A common alternative opt-in enhancement path for a
project like this is to shell out to local CLI-based coding assistant
binaries instead of calling a hosted API — named here for parity, but this
build's validated cloud path is a real hosted API (OpenRouter) instead, per
the project brief.
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


def _generate_local(system: str, user: str, max_new_tokens: int = 400) -> str:
    import torch

    tokenizer, model = _load_local()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.15,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    return text.strip()


def _stream_local(system: str, user: str, max_new_tokens: int = 400):
    """Yields text incrementally as the local model generates it, using
    transformers' TextIteratorStreamer — the model runs in a background
    thread while this generator yields whatever the streamer has produced
    so far, which is what lets the FastAPI route turn this into a real SSE
    stream instead of blocking until the entire answer is done."""
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


def _generate_openrouter(system: str, user: str, max_new_tokens: int = 400) -> str:
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
                {"role": "user", "content": user},
            ],
            "max_tokens": max_new_tokens,
            "temperature": 0.2,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _stream_openrouter(system: str, user: str, max_new_tokens: int = 400):
    """OpenRouter's chat/completions endpoint speaks the same
    OpenAI-compatible SSE format when `stream: true` is set: each event is a
    `data: {...}` line carrying one `choices[0].delta.content` fragment,
    terminated by a literal `data: [DONE]` line."""
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
        f"Only 'local' and 'openrouter' were tested this round. Set the corresponding *_API_KEY_FILE and "
        f"extend llm.py to enable it."
    )


def generate(system: str, user: str, provider: str | None = None, max_new_tokens: int = 400) -> dict:
    provider = provider or settings.llm_provider
    if provider == "local":
        text = _generate_local(system, user, max_new_tokens)
    elif provider == "openrouter":
        text = _generate_openrouter(system, user, max_new_tokens)
    elif provider in ("openai", "anthropic", "gemini"):
        _generate_unavailable(provider)
        text = ""  # unreachable
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return {"text": text, "provider": provider}


def stream_generate(system: str, user: str, provider: str | None = None, max_new_tokens: int = 400):
    """Yields text fragments as they're generated. Same provider routing as
    `generate()`, used by routers/chat.py to build a real SSE response."""
    provider = provider or settings.llm_provider
    if provider == "local":
        yield from _stream_local(system, user, max_new_tokens)
    elif provider == "openrouter":
        yield from _stream_openrouter(system, user, max_new_tokens)
    elif provider in ("openai", "anthropic", "gemini"):
        _generate_unavailable(provider)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def local_model_info() -> dict:
    tokenizer, model = _load_local()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.local_llm_model, "params": n_params, "loaded": True}


def openrouter_available() -> bool:
    return bool(read_key_file(settings.openrouter_api_key_file))
