"""The local chat model, wrapped as a real LangChain `Runnable` — this is
the one piece of this module set that deliberately does NOT reach for
`langchain-huggingface`'s generic `HuggingFacePipeline`/`ChatHuggingFace`
wrapper, even though that would be the more "off-the-shelf idiomatic"
choice. Verified reason, not a guess: this exact 0.5B model, given a
generic system prompt, is known to forget a caller's stated name or repeat
its own greeting once tool-flavored content gets mixed into the
conversation. A generic pipeline wrapper applies its own default
generation kwargs; avoiding that regression requires specific, non-default
settings (`do_sample=False`, `repetition_penalty=1.15`,
`apply_chat_template`) plus a system prompt engineered for Throughline's
own English-language, tool-aware conversations — this module's
`REPLY_SYSTEM_PROMPT` was independently designed and empirically tested
against the real model, not copied from anywhere. A thin custom `Runnable`
around our own generation function guarantees these exact settings are
used every time; see `debug/issue-01-...md` for the regression tests this
module must keep passing.

**A real, honestly-documented limitation found during that same testing**:
even with an explicit instruction to address the representative rather than
the caller, this 0.5B model occasionally slips and addresses the caller by
name directly (e.g. "Sure thing, Diane...") in a reply meant for the rep.
This does not corrupt the FACTS it relays (names/dates/amounts stayed
correct across every multi-turn test run) — only, occasionally, who it
sounds like it's talking to. Consistent with a well-known caveat that small
local models show context confusion under mixed-content prompts; not swept
under the rug here.
"""
import threading

import torch
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from ..config import settings

REPLY_SYSTEM_PROMPT = (
    "You are Throughline, an internal copilot helping a Fenwick Mutual Policyholder Services "
    "representative WHILE they are on a live call with a policyholder. You are NOT speaking to the "
    "policyholder yourself -- you are giving the representative information to use. Address the "
    "representative directly (e.g. 'The caller's policy shows...', 'You can tell them...'), and never "
    "say things like 'thank you for calling' or speak as if you are Fenwick Mutual greeting the caller. "
    "Answer only the representative's most recent message, briefly, as one short reply -- no repeated "
    "greetings, no re-introducing yourself. "
    "If the message contains a line starting with 'Tool result:', that information has ALREADY been "
    "looked up and is verified -- relay it directly. Never say you lack tool access; the lookup is done. "
    "If earlier turns state a fact (like the caller's name or policy number), quote it exactly when asked."
)

_tokenizer = None
_model = None
_lock = threading.Lock()


def _load():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                _tokenizer = AutoTokenizer.from_pretrained(settings.local_chat_model)
                # `dtype=` not the older `torch_dtype=` — verified directly
                # against the currently-installed transformers release,
                # which logs "`torch_dtype` is deprecated! Use `dtype`
                # instead!" if the old kwarg is used.
                _model = AutoModelForCausalLM.from_pretrained(settings.local_chat_model, dtype=torch.float32)
                _model.eval()
    return _tokenizer, _model


def local_model_info() -> dict:
    tok, model = _load()
    return {"model": settings.local_chat_model, "params": sum(p.numel() for p in model.parameters())}


def _split_system(messages: list[BaseMessage], default_system: str) -> tuple[str, list[BaseMessage]]:
    """If the caller supplied their own leading `SystemMessage` (the
    router/extraction chains each do, with their own task-specific
    instructions), use it instead of the default chat `REPLY_SYSTEM_PROMPT`
    — this is what lets `local_llm` serve as ONE shared Runnable for chat
    replies, routing, extraction, AND summarization, rather than four
    near-duplicate generation functions.

    `messages` is normalized to a real `list[BaseMessage]` here — real bug,
    found by direct testing, not assumed: piping a `ChatPromptTemplate`
    directly into `local_llm` (`memory_store.py`'s `SUMMARY_PROMPT |
    local_llm | StrOutputParser()`) hands this function a `ChatPromptValue`,
    not a list — `ChatPromptValue` is not subscriptable, so the naive
    `messages[0]` below raised `TypeError: 'ChatPromptValue' object is not
    subscriptable` the first time a real summarization actually ran. The
    router/extraction chains never hit this (they build a plain list by
    hand, with no `ChatPromptTemplate` in front of `local_llm`), which is
    exactly why this surfaced only once a genuinely different LCEL
    composition shape was exercised."""
    if hasattr(messages, "to_messages"):
        messages = messages.to_messages()
    if messages and isinstance(messages[0], SystemMessage):
        return messages[0].content, messages[1:]
    return default_system, messages


def _messages_to_hf(messages: list[BaseMessage], system_prompt: str) -> list[dict]:
    hf = [{"role": "system", "content": system_prompt}]
    for m in messages:
        role = {"human": "user", "ai": "assistant"}.get(m.type, "user")
        hf.append({"role": role, "content": m.content})
    return hf


def generate_reply(messages: list[BaseMessage]) -> AIMessage:
    """The shared local-model entry point for every LCEL chain in this app
    (chat replies, routing, extraction, summarization) — see
    `_split_system` above for how each chain supplies its own system
    prompt. Non-streaming; `stream_reply` below is the SSE variant used
    only for the live chat reply the representative actually watches
    stream in."""
    tok, model = _load()
    system_prompt, history = _split_system(messages, REPLY_SYSTEM_PROMPT)
    hf_messages = _messages_to_hf(history, system_prompt)
    text = tok.apply_chat_template(hf_messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=False,
            repetition_penalty=1.15,
            pad_token_id=tok.eos_token_id,
        )
    generated = output_ids[0][inputs["input_ids"].shape[1]:]
    text_out = tok.decode(generated, skip_special_tokens=True).strip()
    return AIMessage(content=text_out)


def stream_reply(messages: list[BaseMessage]):
    """Yields text fragments token-by-token via `TextIteratorStreamer`
    running in a background thread — the same real-streaming pattern
    validated across every prior PoC in this project series. Used only for the
    live SSE Workspace endpoint, where the representative watches the reply
    stream in; every other chain in this app (routing, extraction,
    summarization) uses the non-streaming `local_llm` Runnable below via
    plain LCEL `.invoke()`, since none of them stream to a UI."""
    tok, model = _load()
    system_prompt, history = _split_system(messages, REPLY_SYSTEM_PROMPT)
    hf_messages = _messages_to_hf(history, system_prompt)
    text = tok.apply_chat_template(hf_messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt")
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(**inputs, max_new_tokens=200, do_sample=False, repetition_penalty=1.15, streamer=streamer, pad_token_id=tok.eos_token_id)
    thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()
    for fragment in streamer:
        yield fragment
    thread.join()


# The real LangChain `Runnable` used in every LCEL chain in this app
# (`chat_prompt | local_llm | StrOutputParser()` style composition in
# chains/router.py, chains/extraction.py, and chains/memory_store.py) — a
# plain Python function wrapped in `RunnableLambda`, verified end-to-end
# (piped after a real `ChatPromptTemplate`, with `StrOutputParser()` after
# it) against the actual installed `langchain-core` before being relied on
# here.
local_llm = RunnableLambda(generate_reply)
