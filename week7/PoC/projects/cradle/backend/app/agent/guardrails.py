"""The 4 safety guardrails, checked in this order: step limit -> permission
-> cost cap -> HITL.

This order matters: a naive implementation might check the cost cap before
checking tool permission. Reasoned through concretely, that ordering means
calling an unauthorized tool AFTER cost budget is already exhausted would
log `STOPPED_COST_CAP`, not `BLOCKED_PERMISSION` — a security-relevant
"unauthorized tool attempt" event silently mislabeled as an unrelated
budget event, undermining the audit trail's ability to distinguish real
anomalies from routine budget stops. See ../../../debug/issue-01.

Checking permission before cost cap here means an unauthorized-tool attempt
is ALWAYS correctly labeled BLOCKED_PERMISSION, regardless of how much
budget happens to be left at that moment.
"""
from dataclasses import dataclass

from . import tools


@dataclass
class GuardrailVerdict:
    status: str  # ALLOWED | AWAITING_APPROVAL | BLOCKED_PERMISSION | STOPPED_STEP_LIMIT | STOPPED_COST_CAP
    detail: str
    cost: int = 0


def check_guardrails(
    tool_name: str,
    *,
    step_count: int,
    max_steps: int,
    allowed_tools: set[str],
    tool_cost: dict[str, int],
    spent: int,
    cost_cap: int,
    hitl_tools: set[str],
) -> GuardrailVerdict:
    if step_count > max_steps:
        return GuardrailVerdict("STOPPED_STEP_LIMIT", f"Exceeded the maximum of {max_steps} steps.")

    if tool_name not in allowed_tools:
        return GuardrailVerdict("BLOCKED_PERMISSION", f"'{tool_name}' is not on the allowed-tools list.")

    cost = tool_cost.get(tool_name, 5)
    if spent + cost > cost_cap:
        return GuardrailVerdict(
            "STOPPED_COST_CAP",
            f"Cumulative {spent} + this call's {cost} would exceed the cap of {cost_cap}.",
        )

    if tool_name in hitl_tools:
        return GuardrailVerdict("AWAITING_APPROVAL", f"'{tool_name}' requires human approval before running.", cost)

    return GuardrailVerdict("ALLOWED", "ok", cost)


def execute_tool(tool_name: str, arg: str) -> str:
    """Runs a tool's real Python function — only called after
    check_guardrails() has already returned ALLOWED or after a human has
    approved a pending AWAITING_APPROVAL request. Uses ALL_TOOL_FUNCTIONS
    (which includes the never-allowlisted decoy) only so a defensive
    'unknown tool' message is possible; the guardrail check above is what
    actually prevents delete_customer_data from ever reaching here in
    practice."""
    fn = tools.ALL_TOOL_FUNCTIONS.get(tool_name)
    if fn is None:
        return f"Error: unknown tool '{tool_name}'."
    return fn(arg)
