# Issue 01 — Quoted tool arguments silently broke lookups two different ways

**Found**: while visually inspecting the History page's real semantic-search results during
screenshot capture, one run's final answer read "No such procedure exists." for a request about the
total-loss auto and subrogation checklist procedures — both real, present entries in
`_MOCK_PROCEDURES`. Pulling that run's actual trace, and then a second, related run's trace, revealed
two distinct manifestations of the same underlying gap.

## Root cause

`react_loop.py`'s few-shot example only ever demonstrates a bare *numeric* argument
(`Action: estimate_claim_payout(340 - 250)`) — nothing in the prompt tells the model how to format a
*string* or *multi-part* argument. Left to its own conventions (reasonably, mirroring ordinary
function-call syntax from its training), the model produced two different real quoting styles across
two different runs:

**Manifestation 1 — one argument, quoted whole:**
```
Action: lookup_claims_procedure("subrogation")
Observation: No procedure document found for '"subrogation"'. Known topics: total-loss auto, subrogation checklist, ...
```
`lookup_claims_procedure()`'s own matching did `keyword.strip().lower()` — `.strip()` removes
whitespace, not quote characters — so the literal string stayed `'"subrogation"'` (quotes attached),
which is not a substring of the real key `"subrogation checklist"` and doesn't contain it either.

**Manifestation 2 — two arguments, each separately quoted** (the more natural convention for a
multi-argument call in virtually any language the model would have trained on):
```
Action: check_filing_deadline("Belmont Bay", "2025-01-01")
Observation: Error: unknown jurisdiction 'Belmont Bay"'. Known: ASHFORD, BELMONT_BAY, ...
```
An initial fix (stripping one matching layer of quotes from the *whole* captured argument string,
before any comma-splitting) handled Manifestation 1 but actively broke Manifestation 2: stripping
only the very first and very last character of `'"Belmont Bay", "2025-01-01"'` removes the outermost
quote from each end, leaving `Belmont Bay", "2025-01-01` — splitting that on commas gives
`['Belmont Bay"', ' "2025-01-01']`, each still carrying one stray, unmatched quote character. The
resulting jurisdiction key became `'BELMONT_BAY"'` (literal trailing quote), which doesn't match the
real key `BELMONT_BAY` — the lookup failed even though "Belmont Bay" is a real, valid jurisdiction,
and the local model then escalated to OpenRouter, which — reasoning only from the broken observation
it was handed — concluded the user needed to supply an underscore-formatted jurisdiction name, which
is itself not true; it correctly identified a formatting mismatch but for the wrong specific reason,
since it never saw the actual quote-corruption behind it.

## Fix

Replaced the single whole-string strip with two shared helpers in `tools.py`, `clean_arg()` (strips
whitespace and quote characters from one token) and `split_args()` (splits on commas and cleans each
resulting token *independently*, i.e. quote-cleaning happens on the final tokens, not on the raw
joined string before splitting). This is the one approach that handles both real conventions
correctly: for `"A", "B"`, splitting on the comma (which sits outside both quoted regions) cleanly
separates the two tokens before either one's own quotes are stripped; for a hypothetical `"A, B"`
(one argument, quoted whole, with an embedded comma), `clean_arg()` on the whole un-split string
(used by every single-argument tool) still strips the outer pair correctly. Applied consistently
across every tool (`check_filing_deadline`, `lookup_policy_coverage`, `estimate_claim_payout`,
`convert_reinsurance_currency`, `lookup_claims_procedure`, `issue_claim_payout`) and in
`guardrails.py::_parse_payout_amount`, which parses the same raw argument independently for the
amount-aware HITL threshold check and would otherwise fail-safe (force approval) on a quoted amount
that should have been auto-approved.

## Verification

- Reproduced both manifestations directly against the real captured malformed argument strings.
- Added `verify_e2e.py::step_quoted_argument_regression` for Manifestation 1.
- Re-ran the exact Manifestation 2 scenario (`check_filing_deadline("Belmont Bay", "2025-01-01")`)
  live through the Console after the fix and confirmed a correct filing-deadline answer instead of
  an "unknown jurisdiction" error.
- Re-ran the full E2E suite (26/26) and re-captured the affected screenshots on a clean rebuild.
