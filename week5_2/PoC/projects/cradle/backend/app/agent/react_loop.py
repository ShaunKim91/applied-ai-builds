"""The ReAct (Thought -> Action -> Observation) loop, a foundational agentic
pattern, run for real on a local `Qwen2.5-0.5B-Instruct` (same model, same
few-shot-prompting necessity, same generation-truncation guard as a common
baseline approach to this pattern — few-shot examples are load-bearing
here: instructions alone caused the small model to violate the output
format or get arithmetic wrong).

Unlike a typical baseline implementation (one blocking `model.generate()`
call per step), each step streams token-by-token via `TextIteratorStreamer`
— the same real-streaming infrastructure validated in the Week4/5_1
PoCs — so the Console page can render the model's reasoning as it's
actually produced, not just the finished line.
"""
import re
import threading

from ..config import settings

SYSTEM_PROMPT = (
    "You are a tool-using AI agent. Respond with EXACTLY one of two formats, one step at a time:\n\n"
    "Format 1 (need a tool):\nThought: <one line>\nAction: <tool_name>(<input>)\n\n"
    "Format 2 (final answer):\nThought: <one line>\nFinal Answer: <answer>\n\n"
    "Available tools:\n"
    "- calculator(expr): arithmetic. e.g. calculator(127 * 39)\n"
    "- get_today(): today's date, no input needed\n"
    "- convert_currency(amount): converts a KRW amount to USD. e.g. convert_currency(50000)\n"
    "- lookup_faq(keyword): company FAQ lookup, e.g. lookup_faq(refund)\n"
    "- issue_refund(order_id): process a refund for an order (requires human approval)\n\n"
    "If multiple steps are needed, output exactly one Action and stop there."
)


def fewshot_messages() -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "What's your refund policy?"},
        {
            "role": "assistant",
            "content": "Thought: I should look up the refund FAQ.\nAction: lookup_faq(refund)",
        },
        {
            "role": "user",
            "content": "Observation: Refunds are processed within 3 business days of the returned item arriving.",
        },
        {
            "role": "assistant",
            "content": "Thought: I have the answer from the FAQ.\n"
            "Final Answer: Refunds are processed within 3 business days of the returned item arriving.",
        },
    ]


_ACTION_STOP_RE = re.compile(r"^\s*Action:\s*\w+\(.*\)\s*$", re.MULTILINE)


def truncate_generation(raw_text: str) -> str:
    """Stops the kept text at the first complete Action or Final Answer
    line — a common guard used to stop a small model from hallucinating
    its own fake `Observation:` line and continuing to talk to itself."""
    lines = raw_text.split("\n")
    kept = []
    for line in lines:
        kept.append(line)
        if re.match(r"^\s*Action:\s*\w+\(.*\)\s*$", line) or line.strip().startswith("Final Answer:"):
            break
    return "\n".join(kept).strip()


def parse_action(text: str) -> tuple[str, str] | None:
    m = re.search(r"Action:\s*(\w+)\((.*)\)", text)
    return (m.group(1), m.group(2).strip()) if m else None


_lock = threading.Lock()
_tokenizer = None
_model = None


def _load_local():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                from transformers import AutoModelForCausalLM, AutoTokenizer

                _tokenizer = AutoTokenizer.from_pretrained(settings.local_agent_model)
                _model = AutoModelForCausalLM.from_pretrained(settings.local_agent_model)
                _model.eval()
    return _tokenizer, _model


def stream_one_step(messages: list[dict], max_new_tokens: int = 80):
    """Streams ONE ReAct step's raw generation, token by token — the caller
    (routers/agent.py) accumulates the fragments, then applies
    truncate_generation()/parse_action() once the step is complete. Greedy
    decoding (do_sample=False) — ReAct's Thought/Action format is brittle
    enough under a 0.5B model that
    sampling measurably increases format violations (this was tested
    during this build; see debug/ if a real issue was found)."""
    import torch
    from transformers import TextIteratorStreamer

    tokenizer, model = _load_local()
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt")

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=None,
        top_p=None,
        top_k=None,
    )

    def _run():
        with torch.no_grad():
            model.generate(**generation_kwargs)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    for fragment in streamer:
        if fragment:
            yield fragment
    thread.join()


def local_model_info() -> dict:
    tokenizer, model = _load_local()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.local_agent_model, "params": n_params, "loaded": True}
