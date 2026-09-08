"""Tool definitions — a deliberate mix of safe, HITL-gated, and never-
allowlisted "dangerous" tools, a common demonstration pattern for this
kind of guardrail design (a `SAFE_TOOLS` / `ALL_TOOLS` split), extended
with a genuine HITL-gated tool (a typical baseline implementation only has
safe-vs-decoy, no real middle tier) so Cradle's approval queue has
something real to gate.

Execution is entirely our own Python functions — the model can never
fabricate a tool's result, only choose to call one.
"""
import re
from datetime import date

_SAFE_EXPR_RE = re.compile(r"[\d\s+\-*/().]+")


def calculator(expression: str) -> str:
    """Arithmetic only — same regex-restricted `eval` pattern as Week1-13's
    own calculator tools: only digits and `+ - * / ( )` are ever allowed
    through."""
    expression = (expression or "").strip()
    if not expression or not _SAFE_EXPR_RE.fullmatch(expression):
        return "Error: only digits and + - * / ( ) are allowed."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 — regex-restricted above
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


def get_today(_: str = "") -> str:
    return date.today().isoformat()


# A fixed, illustrative rate — this is a demo tool, not a live FX feed (a
# real product would call a real FX API here; see docs/guide.html's
# limitations section for this honestly-disclosed simplification).
_KRW_PER_USD = 1_380.0


def convert_currency(amount_krw: str) -> str:
    """A common introductory example for this kind of tool — converts a
    KRW amount to USD at a fixed illustrative rate."""
    try:
        krw = float(re.sub(r"[^\d.]", "", amount_krw or ""))
    except ValueError:
        return "Error: could not parse a numeric KRW amount."
    usd = krw / _KRW_PER_USD
    return f"≈ ${usd:,.2f} USD (at a fixed illustrative rate of {_KRW_PER_USD:,.0f} KRW/USD)"


_FAQ = {
    "refund": "Refunds are processed within 3 business days of the returned item arriving.",
    "shipping": "Standard shipping takes 2-3 days; remote areas take 3-5 days.",
    "return": "Items can be returned within 14 days of delivery, unused and in original packaging.",
}


def lookup_faq(keyword: str) -> str:
    keyword = (keyword or "").lower()
    for k, v in _FAQ.items():
        if k in keyword:
            return v
    return "No matching FAQ entry found."


def issue_refund(order_id: str) -> str:
    """A genuinely HITL-gated tool — medium risk (spends real money, unlike
    the read-only FAQ/calculator tools) but not catastrophic, exactly the
    tier a typical baseline guardrail design implies but never actually
    implements a real example of (it only has safe-vs-decoy, no real
    middle tier requiring approval). Only reachable at all after an admin
    approves the pending request — see routers/approvals.py."""
    order_id = (order_id or "").strip() or "(unspecified order)"
    return f"Refund issued for order {order_id}."


def delete_customer_data(_: str = "") -> str:
    """The deliberately dangerous decoy tool — intentionally never added to
    any allowlist, so a call always resolves to BLOCKED_PERMISSION
    regardless of guardrail settings. Exists only to prove the permission
    check actually works."""
    return "⚠️ All customer records deleted (demo only — this must never actually execute)."


SAFE_TOOLS = {
    "calculator": calculator,
    "get_today": get_today,
    "convert_currency": convert_currency,
    "lookup_faq": lookup_faq,
}
HITL_TOOLS = {"issue_refund": issue_refund}
# Allowed to run at all (subject to the allowlist + HITL gate) — does NOT
# include delete_customer_data, which exists only as an unregistered
# function so BLOCKED_PERMISSION is demonstrable end to end.
ALLOWED_TOOLS = {**SAFE_TOOLS, **HITL_TOOLS}
HITL_TOOL_NAMES = set(HITL_TOOLS.keys())
ALL_TOOL_FUNCTIONS = {**ALLOWED_TOOLS, "delete_customer_data": delete_customer_data}
