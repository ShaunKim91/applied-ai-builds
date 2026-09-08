"""The ReAct (Thought -> Action -> Observation) loop mechanics: the system
prompt, few-shot examples (a common introductory technique for keeping
small local models on-format — instructions alone cause them to violate
the output format),
action parsing, and a generation-truncation guard preventing the model from
hallucinating its own fake Observation line. Reused pattern from the
predecessor Cradle PoC, retargeted at Threshold's own claims-processing
tool set.
"""
import re
import threading

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from ..config import settings

SYSTEM_PROMPT = """You are Threshold, a claims-processing assistant for Fenwick Mutual. You have access to these tools:

- check_filing_deadline(jurisdiction, loss_date): compute a claim's filing deadline. Arg format: "JURISDICTION, YYYY-MM-DD"
- lookup_policy_coverage(policy_number): look up a policy's coverage limit, deductible, and status
- estimate_claim_payout(expression): evaluate arithmetic (damage estimate minus deductible, etc.)
- convert_reinsurance_currency(amount, currency): convert a foreign-currency amount to USD. Arg format: "AMOUNT, CURRENCY"
- lookup_claims_procedure(keyword): look up an internal SOP/procedure document
- issue_claim_payout(claim_id, amount): issue a payout against a claim. Arg format: "CLAIM_ID, AMOUNT"

Respond using EXACTLY this format, one step at a time:
Thought: <your reasoning>
Action: tool_name(argument)

Wait for the real Observation before continuing. When you have the final answer, respond with:
Thought: <your reasoning>
Final Answer: <your answer>

Never write your own Observation — it will be provided to you."""

_FEWSHOT = [
    {"role": "user", "content": "What is 340 minus a $250 deductible?"},
    {"role": "assistant", "content": "Thought: I need to subtract the deductible from the damage estimate.\nAction: estimate_claim_payout(340 - 250)"},
    {"role": "user", "content": "Observation: 90"},
    {"role": "assistant", "content": "Thought: I have the payout amount.\nFinal Answer: 90"},
]


def fewshot_messages() -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}] + _FEWSHOT


_ACTION_RE = re.compile(r"Action:\s*(\w+)\((.*?)\)", re.DOTALL)
_STOP_MARKERS = ["\nObservation:", "\nThought:", "\nAction:"]


def truncate_generation(raw: str) -> str:
    """Stops the model's own output at the first sign it's hallucinating a
    fake Observation or restarting the Thought/Action cycle on its own —
    the model should only ever produce ONE Thought+Action (or Final Answer)
    per turn; anything after that in the same generation is not trustworthy."""
    text = raw
    # Find the first real Action(...) or Final Answer, then cut anything
    # the model wrote after it.
    action_match = _ACTION_RE.search(text)
    final_idx = text.find("Final Answer:")
    cut_points = []
    if action_match:
        cut_points.append(action_match.end())
    if final_idx != -1:
        # keep the whole rest of the line/paragraph after "Final Answer:"
        next_marker = min((text.find(m, final_idx) for m in _STOP_MARKERS if text.find(m, final_idx) != -1), default=len(text))
        cut_points.append(next_marker)
    if not cut_points:
        return text.strip()
    return text[: min(cut_points)].strip()


def parse_action(gen: str) -> tuple[str, str] | None:
    match = _ACTION_RE.search(gen)
    if not match:
        return None
    # The raw argument is handed to tools.py's own clean_arg()/split_args()
    # helpers UNMODIFIED here — see tools.py's module docstring for why
    # quote-cleaning happens per-final-token there, not on this whole
    # comma-joined string (a single strip here can't correctly handle both
    # `tool("A, B")` and `tool("A", "B")` at once — the two real quoting
    # conventions this build actually observed the model use).
    return match.group(1).strip(), match.group(2).strip()


_tokenizer = None
_model = None
_lock = threading.Lock()


def _load():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                _tokenizer = AutoTokenizer.from_pretrained(settings.local_agent_model)
                _model = AutoModelForCausalLM.from_pretrained(settings.local_agent_model, torch_dtype=torch.float32)
    return _tokenizer, _model


def local_model_info() -> dict:
    tok, model = _load()
    return {"model": settings.local_agent_model, "params": sum(p.numel() for p in model.parameters())}


def stream_one_step(messages: list[dict]):
    """Yields text fragments for exactly one ReAct step (one Thought+Action
    or one Final Answer), streamed token by token via TextIteratorStreamer
    running in a background thread — the same real-streaming pattern
    validated across every prior PoC in this project series."""
    tok, model = _load()
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt")
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(**inputs, max_new_tokens=200, do_sample=False, streamer=streamer, pad_token_id=tok.eos_token_id)
    thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()
    for fragment in streamer:
        yield fragment
    thread.join()
