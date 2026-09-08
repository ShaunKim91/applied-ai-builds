"""The four safety guardrails, in the CORRECTED check order.

A common bug in naive implementations of this pattern checks the cost cap
BEFORE permission/the allowlist — contradicting the intended order of
step-limit -> permission -> cost-cap -> HITL. Practical effect of the bug:
an unauthorized-tool call that happens to occur after the budget is already
exhausted gets logged as `STOPPED_COST_CAP` instead of `BLOCKED_PERMISSION`
— corrupting exactly the anomaly-detection signal an audit trail is meant to
provide. Threshold implements the CORRECT order from the start (already
correct in the predecessor Cradle PoC; carried forward here, not
rediscovered).

**A real engineering upgrade over Cradle**: the old PoC's HITL gate was a
flat per-tool-name set — `issue_refund` was ALWAYS gated regardless of
amount. Threshold's HITL check for `issue_claim_payout` is amount-aware: it
only pauses for approval when the requested payout exceeds an admin-
configurable threshold (`payout_approval_threshold_usd`). An unparseable
amount fails SAFE — i.e. it requires approval — rather than silently
allowing an ambiguous payout through.
"""
from dataclasses import dataclass

from . import tools


@dataclass
class Verdict:
    status: str  # ALLOWED | AWAITING_APPROVAL | BLOCKED_PERMISSION | STOPPED_STEP_LIMIT | STOPPED_COST_CAP
    detail: str = ""
    cost: int = 0


def _parse_payout_amount(arg: str) -> float | None:
    # Uses the same quote-aware splitting as the tool itself (tools.py's
    # split_args) — see debug/issue-01: a quoted amount like
    # issue_claim_payout("CLM-9001", "5000") must parse to a real numeric
    # amount here, not silently fail closed just because the guardrail
    # check's own parsing was less forgiving than the tool's.
    parts = tools.split_args(arg)
    if len(parts) != 2:
        return None
    try:
        return float(parts[1])
    except ValueError:
        return None


def check_guardrails(
    tool_name: str,
    arg: str,
    *,
    step_count: int,
    max_steps: int,
    allowed_tools: set[str],
    tool_cost: dict[str, int],
    spent: int,
    cost_cap: int,
    hitl_tools: set[str],
    payout_approval_threshold_usd: float,
) -> Verdict:
    # 1. Step limit
    if step_count > max_steps:
        return Verdict("STOPPED_STEP_LIMIT", f"Reached the maximum of {max_steps} steps.")

    # 2. Permission (allowlist) — checked BEFORE cost cap, per the corrected
    # order documented above.
    if tool_name not in allowed_tools:
        return Verdict("BLOCKED_PERMISSION", f"'{tool_name}' isn't on the allowed tool list.")

    # 3. Cost cap
    cost = tool_cost.get(tool_name, 5)
    if spent + cost > cost_cap:
        return Verdict("STOPPED_COST_CAP", f"This action (cost {cost}) would exceed the cost cap of {cost_cap}.", cost)

    # 4. HITL — amount-aware for issue_claim_payout, static for any other
    # future HITL-gated tool.
    if tool_name in hitl_tools:
        if tool_name == "issue_claim_payout":
            amount = _parse_payout_amount(arg)
            if amount is None or amount > payout_approval_threshold_usd:
                return Verdict(
                    "AWAITING_APPROVAL",
                    f"Payout of {arg.split(',')[-1].strip() if ',' in arg else arg} exceeds the ${payout_approval_threshold_usd:,.0f} auto-approval threshold (or couldn't be parsed — failing safe).",
                    cost,
                )
        else:
            return Verdict("AWAITING_APPROVAL", f"'{tool_name}' always requires human approval.", cost)

    return Verdict("ALLOWED", "", cost)


def execute_tool(tool_name: str, arg: str) -> str:
    fn = tools.ALLOWED_TOOLS.get(tool_name)
    if fn is None:
        return f"Error: '{tool_name}' is not an executable tool."
    return fn(arg)
