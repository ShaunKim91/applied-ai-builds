# Vibe-Coding Prompt Playbook — Verity (Week6 PoC_v2)

This round's request was structurally different from every prior week: not "build this week's
topic," but "the last two builds didn't have a clear target — start over, name one explicitly, and
raise the engineering bar to commercial-grade." This playbook covers the phases specific to that
kind of request.

## Phase 0 — Diagnose the actual complaint before proposing a fix

> Before designing anything new, verify the complaint is real: read every prior PoC's own README and
> SUMMARY, looking specifically for a stated target customer/industry/persona — not a functional
> category label like "AI Commerce Operations Platform."

**Why**: confirmed via direct quotation, not assumption, that none of the six prior PoCs (including
this project's own predecessor, Compass) had one. This turned a vague "make it clearer" request into
a specific, checkable gap: every future README needs an actual "who this is for" sentence with a
name attached.

## Phase 1 — Pick a target deliberately, and check it against the whole prior body of work

> Before naming a vertical, inventory every prior week's implicit industry/category AND every prior
> week's visual identity (color family + type pairing + navigation pattern), so the new pick doesn't
> quietly repeat either axis.

**Why**: this surfaced that 5 distinct visual identities already existed, and that no prior week had
touched insurance claims — letting the choice (Fenwick Mutual, a P&C insurer) be a genuinely fresh
fit for both project topics (grounded research + safety guardrails) rather than a guess.

## Phase 2 — Design two connected products as one system, not two separate weekly builds

> Given the user wants Week6 and Week7 treated as one company's product suite, design the
> shared narrative, shared design system, and shared "commercial-grade" checklist ONCE, then apply it
> to each product's own concrete feature set — don't design Verity in isolation and improvise
> Threshold's identity later.

**Why**: a plan agent was used specifically to flesh out both products' concrete specs together
(personas, tool sets, design tokens, security checklist) before any code was written, so the two
builds would actually cohere as a suite rather than accidentally diverging.

## Phase 3 — Avoid a real hallucination risk baked into the topic itself

> Insurance claims research inherently involves citing "regulations" and "case law." Before writing
> any seed data, decide explicitly: real jurisdictions with invented facts (risky — could be mistaken
> for real legal information) vs. fully fictional jurisdictions with fictional facts (safe, and
> explicitly disclosed as such).

**Why**: this is a case where the SAFEST design choice was decided architecturally before any
content was written, rather than discovered as a problem after the fact — avoiding a whole class of
"did the model just state real law incorrectly" risk by construction.

## Phase 4 — Build the "commercial-grade" checklist as real code, and know what NOT to build

> Translate "commercial-grade, but still local Docker" into a concrete, scoped checklist (an
> Organization model, rotating auth tokens, CSRF, lockout, a hash-chained audit log, rate limiting,
> real metrics) and equally decide what's explicitly out of scope (real cloud deploy, billing, a
> tenant switcher) — write both down before implementing either.

**Why**: without an explicit boundary, "commercial-grade" scope could expand indefinitely. Writing
the boundary down alongside the checklist kept the actual build focused and made the scope decisions
legible in the final documentation rather than silently implied.

## Phase 5 — Verify a hand-rolled security mechanism by trying to break it, not just exercising it

> For each new security feature (rate limiter, account lockout, refresh-token rotation, audit-log
> hash chain), write a regression test that specifically tries to defeat it — reuse a rotated
> refresh token, exceed the rate limit, tamper with an audit row directly — rather than only testing
> the happy path.

**Why**: a hash chain that's never actually tested against a tampered row could report "intact" for
completely the wrong reason (e.g. a bug that always returns `true`). The direct tamper-then-detect
regression test in `verify_e2e.py` proves the mechanism actually works, not just that it runs.

## Phase 6 — Trust manual visual inspection to catch what automated checks structurally can't

> After the automated E2E suite is fully green, actually look at real screenshots of real model
> output — not just their HTTP status codes.

**Why**: this is exactly how this build's most serious finding (`debug/issue-03` — a hallucinated
real federal agency name scoring a perfect groundedness score) was caught. No HTTP-status-based test
could have found it; only reading the actual rendered text did. The same discipline caught a fraud-
signal false-positive avalanche (`debug/issue-02`) that a green E2E suite had already sailed past.

## Phase 7 — When a test-script wait condition produces a confusing cascading failure, diagnose the actual mechanism before patching around it

> A screenshot script step failed with "no research yet" moments after a real 200 response; the
> NEXT step then timed out entirely. Rather than adding a longer sleep, trace exactly why: a
> streaming endpoint's response event fires on headers, not body completion, and a busy-disabled
> button masked that the second request was never even sent.

**Why**: a longer fixed delay would have "fixed" the symptom without explaining it, and would have
been fragile against any future change in generation speed. Diagnosing the actual mechanism (headers
vs. body, and the busy-flag interaction) produced a fix (wait on a real UI completion signal) that's
correct regardless of how long generation takes.

## General prompting habits used throughout this build

- **Verify a complaint by quoting real evidence, not by agreeing it's probably true** — reading six
  READMEs to confirm zero of them state a persona turned a subjective critique into an objective,
  fixable gap.
- **Decide a content-safety boundary architecturally, before writing content** — fictional
  jurisdictions were a design decision made in Phase 3, not a fix applied after a real-law citation
  slipped through.
- **Test a security mechanism adversarially** — try to reuse the rotated token, try to tamper the
  hash chain — not just confirm the happy path works once.
- **A green automated suite is not the same as a correct product** — this build's two most
  consequential findings were both invisible to `verify_e2e.py` until specifically looked for by
  reading real output.
