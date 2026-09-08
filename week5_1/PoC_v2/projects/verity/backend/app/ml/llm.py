"""Local streaming generation (`Qwen2.5-0.5B-Instruct`) plus an opt-in,
budget-gated OpenRouter escalation (`qwen/qwen3-8b`) — the same two-tier
model-routing pattern validated in the old Compass/Cradle PoCs.

Local generation streams token-by-token via `TextIteratorStreamer` running
in a background thread — the exact pattern reused verbatim across every
prior product in this series since it was first validated.
"""
import threading

import httpx
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from ..config import read_key_file, settings

_tokenizer = None
_model = None
_lock = threading.Lock()

GROUNDING_SYSTEM_PROMPT = (
    "You are Verity, a claims-research assistant for Fenwick Mutual's claims "
    "operations team. Answer ONLY using the numbered sources given to you. "
    "Cite every factual claim with its [n] marker. If the sources don't "
    "support an answer, say so plainly instead of guessing. Never invent a "
    "citation, a regulation, or a case name that isn't in the sources."
)

BRIEF_SYSTEM_PROMPT = (
    "You are Verity, drafting a precedent brief for a Fenwick Mutual claims "
    "file. Using ONLY the numbered sources given, produce exactly these "
    "five sections, each on its own line starting with the exact label: "
    "'Issue:', 'Governing Authority:', 'Facts Applied:', 'Recommendation:', "
    "'Sources:'. Cite every factual claim with its [n] marker. If the "
    "sources don't support a section, write 'Insufficient evidence in the "
    "record.' for that section instead of guessing."
)

ESCALATION_SYSTEM_PROMPT = (
    "You are a senior claims research analyst reviewing a colleague's "
    "in-progress research trace. Given the original question and the trace "
    "so far, give one best-effort, well-cited final answer. Do not invent "
    "sources beyond what the trace already contains."
)


def _load():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                _tokenizer = AutoTokenizer.from_pretrained(settings.local_llm_model)
                _model = AutoModelForCausalLM.from_pretrained(settings.local_llm_model, torch_dtype=torch.float32)
    return _tokenizer, _model


def local_model_info() -> dict:
    tok, model = _load()
    return {"model": settings.local_llm_model, "params": sum(p.numel() for p in model.parameters())}


def stream_generate(system_prompt: str, user_content: str, max_new_tokens: int = 500):
    """Yields text fragments as the local model generates them."""
    tok, model = _load()
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt")
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        streamer=streamer,
        pad_token_id=tok.eos_token_id,
    )
    thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()
    for fragment in streamer:
        yield fragment
    thread.join()


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
                {"role": "user", "content": f"Question: {question}\n\nResearch trace so far:\n{trace_text}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return {"text": text, "model": data.get("model", settings.openrouter_model)}
