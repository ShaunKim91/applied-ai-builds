# Vibe-Coding Prompt Playbook — Threshold (Week7 PoC_v2)

This is the second half of a two-product rebuild (Verity, then Threshold) sharing one company
narrative and one commercial-grade engineering bar. This playbook covers what was specific to
building the *second* product in an already-established suite, rather than repeating Verity's own
phases (research/target-setting/design-system creation) verbatim — see `week6/PoC_v2/prompts/
vibe_coding_prompts.md` for those.

## Phase 0 — Reuse a proven architecture deliberately, don't reinvent it per product

> Before writing any Threshold-specific code, identify exactly which of Verity's just-built
> infrastructure files (auth, audit, rate limiting, metrics, database, vectorstore) are genuinely
> product-agnostic and can be copied with only cosmetic renames, versus which need real
> product-specific redesign (the data model, the business logic).

**Why**: `security.py` and `audit.py` were copied verbatim (same architecture, same rationale docstrings) —
zero risk of the two products' auth model silently diverging. `models.py` was NOT copied — it needed
a genuinely different schema (`AgentRun`/`ApprovalRequest`/`GuardrailSetting` vs. Verity's
`ResearchSession`/`ReportEntry`/`CatEvent`). Knowing which is which before starting saved real time
and kept the shared security architecture provably identical rather than "close enough."

## Phase 1 — Redesign a tool set as a genuine upgrade, not a reskin

> Before renaming Cradle's six tools to claims-processing equivalents, ask what a REAL upgrade to
> the underlying mechanism would look like, not just new names for the same behavior. Specifically:
> Cradle's HITL gate was a flat per-tool-name set; does this domain (claims payouts) suggest a
> sharper, more realistic guardrail?

**Why**: this produced the round's single most meaningful engineering delta — amount-aware HITL. A
real claims team's actual policy is never "always require approval for any refund," it's "require
approval above a threshold." Naming the tools "issue_claim_payout" without also upgrading the
guardrail logic itself would have been a reskin, not an upgrade.

## Phase 2 — Carry forward a prior build's own bugs as regression tests, not just as fixed code

> Before writing `orchestrator.py`, list every real bug the predecessor Cradle PoC found and fixed
> (guardrail order, the stale-run reaper, step-numbering consistency, the Final Answer streaming
> clear) and write each one's regression test FIRST, then implement the code that should already
> pass it.

**Why**: this build shipped zero of Cradle's own six bugs — not because the domain avoided them by
luck, but because each was a known, specific, testable failure mode checked from day one. Compare
this to Verity, which found three NEW bugs of its own despite the same discipline — proof the
discipline works for known failure modes but doesn't substitute for genuinely testing new surface
area (see Phase 3).

## Phase 3 — A new, richer tool surface will find new failure modes a prior build's testing never exercised

> Don't assume a proven ReAct/tool-calling pattern is bug-free just because a prior build using it
> passed all its tests — a genuinely different tool surface (more string arguments, more
> multi-part arguments) can exercise code paths the prior build's tools never touched.

**Why**: Cradle's own tools were either purely numeric or simple pairs the model happened not to
quote during that build's testing — so quote-handling was never exercised there. Threshold's
richer, more string-heavy tools gave the model real reason to quote arguments, surfacing a genuine
gap in argument parsing that had nothing to do with this build's own new code being sloppy — it was
latent in the shared `parse_action()` pattern all along, just never triggered before.

## Phase 4 — When a first fix passes its own test but might not generalize, actively look for the second failure mode

> After fixing the first observed quoting failure, don't stop at "the test I wrote now passes" —
> actively construct the OTHER plausible way a model might format a similar argument, and check
> whether the same fix handles it too.

**Why**: this is exactly how Manifestation 2 (two separately-quoted arguments) was caught — by
asking "what's the other natural way a model would format a multi-argument call?" rather than
declaring victory after the first fix passed its own narrow test. The first fix's approach (strip
quotes from the whole joined string, then split) actively broke this second case; only checking for
it revealed that the fix needed a fundamentally different structure (clean each final token
independently), not just a patch.

## General prompting habits used throughout this build

- **Reuse infrastructure verbatim only when it's genuinely product-agnostic** — copy `security.py`,
  redesign `models.py`; know the difference before starting.
- **A domain redesign is an opportunity to upgrade a mechanism, not just rename it** — amount-aware
  HITL came from asking what this domain's REAL guardrail need is, not from a thesaurus pass over
  Cradle's tool names.
- **Carrying forward a prior build's bugs as regression tests is real risk reduction, but it isn't
  exhaustive** — a genuinely new surface area (richer tool arguments) can and did find something new.
- **After a fix passes its own test, actively construct the fix's OWN plausible failure mode before
  declaring it done** — this caught a second real bug the first fix would otherwise have silently
  shipped.
