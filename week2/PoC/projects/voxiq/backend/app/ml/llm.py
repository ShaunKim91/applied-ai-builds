"""Models 4 & 5 / 6 — the Analytics Agent's code-generation brain.

Local Qwen2.5-0.5B-Instruct is the default, no-key-required path — a small,
capable open-weight model well-suited to fully offline, no-API-key text/code
generation. OpenRouter's qwen/qwen3-8b is a strictly opt-in, user-toggled
upgrade — validated with a real key this round, per the project brief.
OpenAI/Anthropic/Gemini are scaffolded (config fields exist in config.py) but
NOT validated: calling them raises a clear NotImplementedError instead of
silently pretending to work. This mirrors backend/app/ml/llm.py from an
earlier product in this series, CommerceIQ, almost exactly — the same hybrid
"local default, cloud opt-in" pattern applies to a different feature here
(Python code generation instead of a forecast narrative).
"""
import threading

from ..config import settings, read_key_file

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


def _generate_local(system: str, user: str, max_new_tokens: int = 300) -> str:
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


def _generate_openrouter(system: str, user: str, max_new_tokens: int = 300) -> str:
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


def _generate_unavailable(provider: str):
    raise NotImplementedError(
        f"'{provider}' provider is scaffolded (config/env-var ready) but not validated in this build. "
        f"Only 'local' and 'openrouter' were tested this round. Set the corresponding *_API_KEY_FILE and "
        f"extend llm.py to enable it."
    )


def generate(system: str, user: str, provider: str | None = None, max_new_tokens: int = 300) -> dict:
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


def local_model_info() -> dict:
    tokenizer, model = _load_local()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.local_llm_model, "params": n_params, "loaded": True}


def openrouter_available() -> bool:
    return bool(read_key_file(settings.openrouter_api_key_file))
