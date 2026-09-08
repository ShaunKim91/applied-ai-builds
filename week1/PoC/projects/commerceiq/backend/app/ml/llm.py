"""Model 4 & 5 / 5 — narrative / insight-generation LLM, hybrid local+cloud.

Follows the same "hybrid architecture" convention used consistently across
this project series: a local model is ALWAYS the default and always works
with zero API keys; a cloud model is a strictly opt-in upgrade that fails
independently without breaking the default path.

- provider="local" (default): Qwen/Qwen2.5-0.5B-Instruct, a well-established
  small local LLM choice, run fully offline.
- provider="openrouter": qwen/qwen3-8b via OpenRouter — cheap
  ($0.117/$0.455 per M tokens as of Aug 2026), validated with a real request
  in this build. Key is read from api_keys/openrouter.md (never hardcoded).
- provider in ("openai", "anthropic", "gemini"): configuration is scaffolded
  (see config.py's *_api_key_file fields) so a real deployment can add them,
  but they are NOT exercised/validated in this round — calling them raises
  NotImplementedError with a clear message rather than silently pretending
  to work.
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


def _generate_local(system: str, user: str, max_new_tokens: int) -> str:
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


def _generate_openrouter(system: str, user: str, max_new_tokens: int) -> str:
    import httpx

    key = read_key_file(settings.openrouter_api_key_file)
    if not key:
        raise RuntimeError(f"OpenRouter API key not found at {settings.openrouter_api_key_file}")
    response = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_new_tokens,
            "temperature": 0.3,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def generate(system: str, user: str, provider: str | None = None, max_new_tokens: int = 220) -> dict:
    provider = provider or settings.llm_provider
    if provider == "local":
        text = _generate_local(system, user, max_new_tokens)
    elif provider == "openrouter":
        text = _generate_openrouter(system, user, max_new_tokens)
    elif provider in ("openai", "anthropic", "gemini"):
        raise NotImplementedError(
            f"'{provider}' is configured (see config.py / .env.example) but not validated in this "
            f"build round. Only 'local' and 'openrouter' were exercised end-to-end. Implement the "
            f"provider's request in llm.py and re-run scripts/verify_e2e.sh before relying on it."
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return {"text": text, "provider": provider}


def local_model_info() -> dict:
    _, model = _load_local()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.local_llm_model, "params": n_params, "loaded": True}


def openrouter_available() -> bool:
    return bool(read_key_file(settings.openrouter_api_key_file))
