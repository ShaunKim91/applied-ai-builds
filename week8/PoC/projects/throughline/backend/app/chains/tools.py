"""Throughline's tool set — five safe, informational, deterministic Python
functions. Deliberately does NOT include anything payout-capable: that risk
surface belongs to Threshold (Week7), which already implements guarded,
amount-aware HITL for real fund movement. Throughline's differentiator is
conversational continuity, not risk-gated action-taking, so no tool here
needs a HITL gate — this project's own guardrail axis is the memory-write
conflict check in chains/extraction.py instead.

Unlike Threshold's ReAct loop (a free-text "Action: tool(arg)" line the
model must format and this app must then parse — see Threshold's
`clean_arg`/`split_args` and the two-manifestation quoting bug that drove
them), Throughline's router (chains/router.py) produces already-structured,
already-typed JSON arguments via a Pydantic schema. So there is no
quote-stripping/comma-splitting layer here to get subtly wrong — each tool
below takes its arguments as a plain Python dict, already validated by the
router's schema before it ever reaches this module.

Data shape is deliberately NOT the same as Threshold's `lookup_policy_coverage`
(coverage limit / deductible): `lookup_caller_account` returns billing/
contact-administration fields instead — the things a Policyholder Services
rep actually needs turn to turn, not what a claims examiner needs. Same
underlying fictional Fenwick Mutual policy-number format (`FM-######`) for
world-consistency with Verity/Threshold, but an independent small dataset —
each product stays self-contained (no runtime or code dependency on another
product's tree).
"""
from ..ml.safe_eval import UnsafeExpressionError, safe_eval

_MOCK_ACCOUNTS: dict[str, dict] = {
    "FM-100234": {"billing_status": "ACTIVE", "next_payment_due": "2026-09-15", "preferred_contact": "EMAIL", "last_contact_date": "2026-07-02"},
    "FM-100891": {"billing_status": "ACTIVE", "next_payment_due": "2026-09-28", "preferred_contact": "PHONE", "last_contact_date": "2026-08-11"},
    "FM-101477": {"billing_status": "PAST_DUE", "next_payment_due": "2026-08-20", "preferred_contact": "EMAIL", "last_contact_date": "2026-08-25"},
}

_MOCK_FAQ: dict[str, str] = {
    "autopay enrollment": "To enroll in autopay: the policyholder confirms a payment method on file, then autopay activates on the next billing cycle (not retroactive to the current cycle).",
    "paperless billing": "To switch to paperless billing: update the contact preference to EMAIL (see lookup_caller_account) and confirm the policyholder's current email address is on file.",
    "address change": "Address changes take effect on the next renewal unless the policyholder specifically requests a mid-term endorsement, which may affect the premium if it changes rating territory.",
    "cancellation for nonpayment": "A PAST_DUE account enters a 10-day grace period from the due date before cancellation-for-nonpayment processing begins; a payment posted within that window fully reinstates the policy with no lapse.",
}

_CALLBACK_SLOTS: dict[str, list[str]] = {
    "billing": ["Tomorrow 10:00 AM", "Tomorrow 2:00 PM", "Thursday 11:00 AM"],
    "underwriting": ["Tomorrow 1:00 PM", "Friday 9:00 AM"],
    "claims support": ["Today 4:00 PM", "Tomorrow 9:30 AM"],
    "policy changes": ["Tomorrow 3:00 PM", "Thursday 10:00 AM"],
}


def lookup_caller_account(policy_number: str) -> str:
    key = (policy_number or "").strip().upper()
    account = _MOCK_ACCOUNTS.get(key)
    if not account:
        return f"Tool result: Error - no account found for policy '{policy_number}'."
    return (
        f"Tool result: Policy {key} — billing status {account['billing_status']}, "
        f"next payment due {account['next_payment_due']}, preferred contact {account['preferred_contact']}, "
        f"last contact {account['last_contact_date']}."
    )


def estimate_premium_adjustment(expression: str) -> str:
    try:
        result = safe_eval(expression or "")
    except UnsafeExpressionError as exc:
        return f"Tool result: Error - could not compute '{expression}' ({exc}); please provide a plain numeric expression."
    return f"Tool result: {expression.strip()} = {result:g}"


def lookup_billing_faq(keyword: str) -> str:
    key = (keyword or "").strip().lower()
    for k, v in _MOCK_FAQ.items():
        if key and (key in k or k in key):
            return f"Tool result: {v}"
    return f"Tool result: Error - no billing/account procedure found for '{keyword}'. Known topics: {', '.join(_MOCK_FAQ)}."


# "morning"/"afternoon" is how a caller's preference actually gets stated
# and extracted (see chains/extraction.py) but the fixed slot table below is
# stamped "10:00 AM"/"2:00 PM" — found via direct testing that a literal
# substring match between the two never fires, silently falling through to
# "list everything" every time despite a real stated preference being on
# file. AM/PM before noon maps to "morning", noon-or-later to "afternoon".
def _slot_period(slot: str) -> str:
    return "morning" if "AM" in slot.upper() else "afternoon"


def check_callback_availability(department: str, preferred_window: str = "") -> str:
    key = (department or "").strip().lower()
    slots = _CALLBACK_SLOTS.get(key)
    if not slots:
        return f"Tool result: Error - unknown department '{department}'. Known: {', '.join(_CALLBACK_SLOTS)}."
    if preferred_window:
        pref = preferred_window.lower()
        matches = [s for s in slots if pref in s.lower() or pref in _slot_period(s)]
        if matches:
            return f"Tool result: {matches[0]} is available with {department} (matches the caller's stated preference of {preferred_window})."
    return f"Tool result: Next available {department} callback slots: {', '.join(slots)}."


def flag_for_escalation(reason: str) -> str:
    reason = (reason or "").strip() or "(no reason given)"
    return f"Tool result: Escalation flagged for supervisor review — reason: {reason}."


TOOLS = {
    "lookup_caller_account": lookup_caller_account,
    "estimate_premium_adjustment": estimate_premium_adjustment,
    "lookup_billing_faq": lookup_billing_faq,
    "check_callback_availability": check_callback_availability,
    "flag_for_escalation": flag_for_escalation,
}
