"""Structured-output tool routing — the real replacement for a typical
regex `_route()` (documented false negative: "12에 8을 곱하면?" never
triggers `calc` since there's no literal `*`). Uses a Pydantic schema +
`PydanticOutputParser` (real `langchain-core` output parsing) instead of
keyword matching.

**Honestly measured, not assumed, before this was written**: directly
tested against the real local model with 6 realistic representative
messages before writing this module. Result: 2 of 6 produced a
schema-valid, fully correct decision on the first attempt; the other 4 each
failed a different way — a hallucinated tool name never in the schema
("multiply_numbers"), an invented field name not in any tool's arg shape
("callback_date" instead of "preferred_window"), a non-numeric placeholder
substituted into an arithmetic expression ("base + 45" instead of the
actual number from context), and an invalid `action` value carrying a tool
name instead of "tool"/"reply". A one-shot retry with the validation error
appended sometimes fixes this (case 3) and sometimes reproduces the exact
same malformed output verbatim (case 6, the hallucinated tool name) — so
this module does NOT loop indefinitely hoping a retry eventually works. See
`debug/issue-02-router-structured-output-reliability.md` for the full
before/after transcripts this design is based on.

**The honest fallback** (per this project's own explicit design principle:
never silently pretend nothing happened): after one retry, if the decision
still doesn't validate, this module does NOT guess a tool or discard the
message — it falls back to `action="reply"`, letting the same local model
answer directly in its own words (which, per the same empirical testing,
tends to ask a clarifying question when it lacks a concrete detail to act
on). Every routing attempt — first-try success, retry-recovered, or
fallback — is returned in `RouterResult` so `chains/orchestrator.py` can
write an honest audit-log entry, building a real measured reliability
statistic across the E2E suite rather than an assumed one.
"""
import json
from dataclasses import dataclass
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, ValidationError

from .llm_runnable import local_llm
from .tools import TOOLS

# Real LCEL composition (`Runnable | Runnable`), per D1's own lesson — the
# routing chain is `local_llm` (itself a Runnable, see llm_runnable.py) piped
# into `StrOutputParser()`, which unwraps the `AIMessage` it returns into a
# plain string. Schema validation happens as an explicit Python step after
# `.invoke()`, not inside the chain — the retry-with-feedback control flow
# below genuinely needs branching a single linear LCEL pipe doesn't express
# any more clearly than plain Python does.
_route_chain = local_llm | StrOutputParser()

_TOOL_NAMES = sorted(TOOLS.keys())

ROUTER_SYSTEM_PROMPT = f"""You are a routing engine for a Fenwick Mutual contact-center copilot. Given a representative's message (and any case context provided), decide whether it needs a tool call or a direct reply. Respond with ONLY a single JSON object, no other text, matching this schema:
{{"action": "tool" or "reply", "tool_name": one of {_TOOL_NAMES} or null, "tool_args": an object matching the chosen tool, or {{}} for "reply"}}

Tool argument shapes:
- lookup_caller_account: {{"policy_number": string}}
- estimate_premium_adjustment: {{"expression": string}} -- ALWAYS substitute the actual numbers already mentioned in the conversation; never use a placeholder word like "base" or a variable name.
- lookup_billing_faq: {{"keyword": string}}
- check_callback_availability: {{"department": one of "billing","underwriting","claims support","policy changes", "preferred_window": string or ""}}
- flag_for_escalation: {{"reason": string}}

Examples:
Message: "Look up policy FM-100234"
{{"action": "tool", "tool_name": "lookup_caller_account", "tool_args": {{"policy_number": "FM-100234"}}}}

Message: "The base premium is 210, add a 45 surcharge, what's the total?"
{{"action": "tool", "tool_name": "estimate_premium_adjustment", "tool_args": {{"expression": "210 + 45"}}}}

Message: "What's our policy on paperless billing?"
{{"action": "tool", "tool_name": "lookup_billing_faq", "tool_args": {{"keyword": "paperless billing"}}}}

Message: "Can you get a billing callback slot, they prefer afternoons?"
{{"action": "tool", "tool_name": "check_callback_availability", "tool_args": {{"department": "billing", "preferred_window": "afternoon"}}}}

Message: "This one needs a supervisor, the caller is disputing a closed claim"
{{"action": "tool", "tool_name": "flag_for_escalation", "tool_args": {{"reason": "caller disputing a closed claim"}}}}

Message: "Thanks, that's all I needed"
{{"action": "reply", "tool_name": null, "tool_args": {{}}}}
"""


class RouterDecision(BaseModel):
    action: Literal["tool", "reply"]
    tool_name: Optional[str] = None
    tool_args: dict = {}


@dataclass
class RouterResult:
    decision: RouterDecision
    attempts: int
    fell_back: bool
    raw_first: str = ""
    raw_final: str = ""


def _parse_and_validate(raw: str) -> RouterDecision | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    try:
        decision = RouterDecision.model_validate(data)
    except ValidationError:
        return None
    if decision.action == "tool" and decision.tool_name not in TOOLS:
        return None
    return decision


def route(user_content: str) -> RouterResult:
    base_messages = [SystemMessage(content=ROUTER_SYSTEM_PROMPT), HumanMessage(content=f'Message: "{user_content}"')]
    raw1 = _route_chain.invoke(base_messages)
    decision = _parse_and_validate(raw1)
    if decision is not None:
        return RouterResult(decision=decision, attempts=1, fell_back=False, raw_first=raw1, raw_final=raw1)

    retry_messages = base_messages + [
        AIMessage(content=raw1),
        HumanMessage(content="That did not match the required schema exactly. Respond again with ONLY a corrected JSON object."),
    ]
    raw2 = _route_chain.invoke(retry_messages)
    decision = _parse_and_validate(raw2)
    if decision is not None:
        return RouterResult(decision=decision, attempts=2, fell_back=False, raw_first=raw1, raw_final=raw2)

    fallback = RouterDecision(action="reply", tool_name=None, tool_args={})
    return RouterResult(decision=fallback, attempts=2, fell_back=True, raw_first=raw1, raw_final=raw2)
