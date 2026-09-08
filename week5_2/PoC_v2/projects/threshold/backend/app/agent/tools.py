"""Threshold's tool set — a complete, claims-processing-themed redesign of
the old Cradle PoC's six generic tools (calculator/get_today/
convert_currency/lookup_faq/issue_refund/delete_customer_data), not a
reskin: one new tool (`lookup_policy_coverage`) reflects a real distinct job
Priya's examiners do that the old six didn't cover.

Every tool is a real, deterministic Python function — the model chooses a
tool and an argument, but never fabricates a result; execution always
happens here. See config.py's `default_tool_cost` for the cost-unit
rationale and `guardrails.py` for how risk tier maps to enforcement.

**A real bug found via manual testing, and its fix** (see debug/issue-01):
the few-shot example in react_loop.py only demonstrates a bare NUMERIC
argument (`estimate_claim_payout(340 - 250)`), so nothing teaches the model
how to format a multi-part or string argument. Left to its own conventions
the model reasonably produced BOTH real quoting styles ordinary code would
use: a whole argument wrapped in quotes (`lookup_claims_procedure("subrogation")`)
AND each comma-separated part separately quoted
(`check_filing_deadline("Belmont Bay", "2025-01-01")`, actually observed).
`clean_arg()`/`split_args()` below strip quote characters from each FINAL
token independently (after any comma-splitting), which is the one approach
that handles both conventions correctly — stripping quotes from the whole
raw string BEFORE splitting only fixes the first convention and actively
corrupts the second (it removes the outermost quote from each end of the
whole string, leaving one stray unmatched quote attached to each inner
part). Every tool below uses these instead of a bare `.split(",")`.
"""
import re

_QUOTE_CHARS = " \t'\""


def clean_arg(s: str) -> str:
    """Strips whitespace and any quote characters from both ends of a
    single token — safe to call on an argument that was never quoted at
    all (a no-op in that case)."""
    return s.strip(_QUOTE_CHARS)


def split_args(arg: str) -> list[str]:
    """Splits a raw multi-part argument on commas and cleans each resulting
    token independently — see this module's docstring for why cleaning
    happens per-final-token, not on the whole joined string."""
    return [clean_arg(p) for p in arg.split(",")]

# A small, fixed, explicitly fictional set of filing-deadline periods per
# jurisdiction (days from loss date) — mirrors Verity's own fictional
# jurisdiction corpus (Ashford/Belmont Bay/Cedermoor/Dunraven/Elmsworth/
# Fairhaven) so the two products' world stays internally consistent, even
# though they don't share a database or any live integration.
_FILING_DEADLINES_DAYS = {
    "ASHFORD": 365,
    "BELMONT_BAY": 730,
    "CEDERMOOR": 545,
    "DUNRAVEN": 400,
    "ELMSWORTH": 545,
    "FAIRHAVEN": 365,
}

# A small, fixed mock policy-admin table — deterministic, not a real
# customer database. Keyed by a plausible policy-number format.
_MOCK_POLICIES = {
    "FM-100234": {"coverage_limit": 250000, "deductible": 1000, "jurisdiction": "Cedermoor", "status": "active"},
    "FM-100891": {"coverage_limit": 500000, "deductible": 2500, "jurisdiction": "Fairhaven", "status": "active"},
    "FM-101477": {"coverage_limit": 150000, "deductible": 500, "jurisdiction": "Ashford", "status": "lapsed"},
}

_MOCK_PROCEDURES = {
    "total-loss auto": "For a total-loss auto claim: (1) confirm actual cash value via two independent valuation sources, (2) verify lienholder payoff, (3) issue payout only after title transfer paperwork is initiated.",
    "subrogation checklist": "Subrogation checklist: identify at-fault third party, confirm their carrier, send a subrogation demand within 30 days of payout, track recovery against the claim file.",
    "coastal wind/hail": "Coastal wind/hail claims: confirm whether the policy discloses a separate wind/hail deductible on the declarations page per Fairhaven Rev. Code § 61.335 — if not disclosed there, apply the standard deductible instead.",
    "reinsurance recovery": "Reinsurance recovery claims: record the exact FX conversion rate and date used, per Elmsworth Ins. Reg. 12 VAC 90-40 — the rate must be no more than 3 business days stale at settlement.",
}

_FX_RATES_TO_USD = {"EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "JPY": 0.0067, "AUD": 0.66}

_SAFE_EXPR_RE = re.compile(r"^[\d\s+\-*/().]+$")


def check_filing_deadline(arg: str) -> str:
    """arg format: 'STATE_CODE, YYYY-MM-DD' e.g. 'CEDERMOOR, 2025-06-01'."""
    parts = split_args(arg)
    if len(parts) != 2:
        return "Error: expected 'JURISDICTION, YYYY-MM-DD'"
    state_code, loss_date_str = parts
    key = state_code.upper().replace(" ", "_")
    days = _FILING_DEADLINES_DAYS.get(key)
    if days is None:
        return f"Error: unknown jurisdiction '{state_code}'. Known: {', '.join(_FILING_DEADLINES_DAYS)}"
    try:
        import datetime as dt

        loss_date = dt.date.fromisoformat(loss_date_str)
    except ValueError:
        return "Error: loss date must be YYYY-MM-DD"
    import datetime as dt

    deadline = loss_date + dt.timedelta(days=days)
    return f"Filing deadline for a loss in {state_code} on {loss_date_str}: {deadline.isoformat()} ({days} days)."


def lookup_policy_coverage(policy_number: str) -> str:
    policy = _MOCK_POLICIES.get(clean_arg(policy_number).upper())
    if not policy:
        return f"No policy found for '{policy_number}'."
    return (
        f"Policy {policy_number}: coverage limit ${policy['coverage_limit']:,}, "
        f"deductible ${policy['deductible']:,}, jurisdiction {policy['jurisdiction']}, status {policy['status']}."
    )


def estimate_claim_payout(expression: str) -> str:
    expr = clean_arg(expression)
    if not _SAFE_EXPR_RE.match(expr):
        return "Error: only digits and + - * / ( ) are allowed."
    try:
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307 — regex-restricted above
    except Exception as exc:  # noqa: BLE001
        return f"Error evaluating expression: {exc}"
    return f"{result}"


def convert_reinsurance_currency(arg: str) -> str:
    """arg format: 'AMOUNT, CURRENCY' e.g. '10000, EUR'."""
    parts = split_args(arg)
    if len(parts) != 2:
        return "Error: expected 'AMOUNT, CURRENCY'"
    amount_str, currency = parts
    try:
        amount = float(amount_str)
    except ValueError:
        return "Error: amount must be numeric"
    rate = _FX_RATES_TO_USD.get(currency.upper())
    if rate is None:
        return f"Error: unknown currency '{currency}'. Known: {', '.join(_FX_RATES_TO_USD)}"
    usd = amount * rate
    return f"{amount} {currency.upper()} = ${usd:,.2f} USD (illustrative fixed rate {rate}, per Elmsworth Ins. Reg. 12 VAC 90-40 disclosure convention)."


def lookup_claims_procedure(keyword: str) -> str:
    key = clean_arg(keyword).lower()
    for k, v in _MOCK_PROCEDURES.items():
        if key in k or k in key:
            return v
    return f"No procedure document found for '{keyword}'. Known topics: {', '.join(_MOCK_PROCEDURES)}"


def issue_claim_payout(arg: str) -> str:
    """arg format: 'CLAIM_ID, AMOUNT' e.g. 'CLM-4471, 1800'. Real execution
    only ever happens after guardrails.check_guardrails() has cleared it —
    either it was under the approval threshold, or a human approved it."""
    parts = split_args(arg)
    if len(parts) != 2:
        return "Error: expected 'CLAIM_ID, AMOUNT'"
    claim_id, amount_str = parts
    try:
        amount = float(amount_str)
    except ValueError:
        return "Error: amount must be numeric"
    return f"Payout of ${amount:,.2f} issued for claim {claim_id}. (Illustrative demo transaction — not a real payment.)"


def close_and_purge_claim_file(claim_id: str) -> str:
    """Deliberately never allowlisted — see guardrails.py's ALLOWED_TOOLS.
    Exists only as a decoy: if a compromised/misbehaving agent ever tries to
    call it, check_guardrails() blocks it on the PERMISSION check before
    this function is ever reached."""
    return f"(This should never execute — close_and_purge_claim_file is never in ALLOWED_TOOLS. claim_id={claim_id})"


SAFE_TOOLS = {
    "check_filing_deadline": check_filing_deadline,
    "lookup_policy_coverage": lookup_policy_coverage,
    "estimate_claim_payout": estimate_claim_payout,
    "convert_reinsurance_currency": convert_reinsurance_currency,
    "lookup_claims_procedure": lookup_claims_procedure,
}
HITL_TOOLS = {"issue_claim_payout": issue_claim_payout}
ALLOWED_TOOLS = {**SAFE_TOOLS, **HITL_TOOLS}
HITL_TOOL_NAMES = set(HITL_TOOLS.keys())
ALL_TOOL_FUNCTIONS = {**ALLOWED_TOOLS, "close_and_purge_claim_file": close_and_purge_claim_file}
