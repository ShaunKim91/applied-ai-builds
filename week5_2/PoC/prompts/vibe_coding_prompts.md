# Vibe-Coding Prompt Playbook — Cradle (Week5_2 PoC)

This is the prompt sequence someone could actually use — with an AI coding tool such as Claude
Code — to reproduce a project like Cradle from scratch. It mirrors the Week1-14_1 PoCs' own
playbooks in structure, with new phases this round for a design brief phrased as qualitative
properties ("genuine 3D," "pastel," "not simply made") rather than a feature list, and for a
safety-guardrails topic whose typical baseline implementation contains an easy-to-make bug worth
correcting rather than reproducing.

## Phase 0 — Research before touching code, including verifying assumed behavior, not just reading about it

> Summarize the agentic AI fundamentals this build is based on (the ReAct loop, local-LLM agents, the
> four safety guardrails, a "vibe coding" tool-evaluation framework applied to agent frameworks) and
> a typical baseline implementation's exact behavior — including checking whether such an
> implementation actually does what its own stated design intent claims it does.

**Why the second half matters**: this specifically caught that a typical baseline guardrail class
checks cost cap *before* permission, directly contradicting its own stated design intent — found by
tracing the actual guardrail-check function's logic order, not by trusting a narrative description.
Also caught: a typical baseline implementation builds `approval_required_tools` as a real class
feature but never populates it in the shipped app, so its own headline HITL guardrail never actually
triggers in the demo.

## Phase 1 — Turn a qualitative design brief into structural, checkable deltas

> This round's brief was explicitly qualitative: "not simple coding — raise the quality, add genuine
> 3D and spatial depth, high lightness/low saturation pastel, not a simply-made UI." Before writing
> any code, name the exact structural deltas versus last week's build (Week5_1 "Compass"): a new
> color system defined by lightness/saturation targets (not just new hex values), a genuinely new
> *interaction category* (a real pointer-reactive 3D transform, not a static shadow), and a new
> visualization concept tied to this week's own subject matter (a layered card stack mirroring the
> ReAct loop's own "steps stack up" structure).

**Why**: "add 3D" is unverifiable on its own. Naming the specific technique (CSS `perspective` +
`rotateX`/`rotateY` driven by real `pointermove` coordinates, not a fixed decorative tilt) made it
possible to check afterward that the result was actually spatial, not just visually busier.

## Phase 2 — Verify a claimed guardrail-ordering pitfall by tracing it directly, not just assuming it

> Before writing a single line of the corrected guardrail order, actually trace through the exact
> scenario by hand: an unauthorized tool call that also exceeds the cost cap. Confirm which guardrail
> would actually fire first under a naive ordering, and write down the exact observable difference
> (which status string ends up in the audit log) that ordering produces.

**Why**: a claimed bug that turns out to be a misreading wastes the rest of the build correcting
something that wasn't wrong. Confirming it concretely — cost cap firing first really does produce
`STOPPED_COST_CAP` instead of `BLOCKED_PERMISSION` for that exact scenario — made the correction
(and its regression test) something you could actually verify passed, not just something that
looked more correct.

## Phase 3 — Scaffold, reusing infrastructure files verbatim where safe

> Copy every backend file with no project-specific business logic (`security.py`, `database.py`,
> `audit.py`, `state.py`, `vectorstore.py`, the auth router, `ml/embeddings.py`, the daily-budget-cap
> governance pattern) from the most recent prior project (Week5_1 Compass). Write new modules only
> for what's genuinely new this week (`agent/tools.py`, `agent/react_loop.py`,
> `agent/guardrails.py`, `agent/orchestrator.py`, the approvals router).

**Applying a lesson instead of re-discovering it**: `orchestrator.py::run_react_loop()` opens its own
fresh `SessionLocal()` from the start, rather than a `Depends(get_db)`-injected session — not
because a bug was found this week, but because the *exact same* session-lifecycle mismatch was a
real, documented lesson from Week4's own debug log (a dependency-injected session closes when the
route handler returns, before a streaming generator body finishes).

## Phase 4 — Backend: design the resumable-run data model before writing the loop

> Before writing `run_react_loop()`, decide what has to be persisted for a paused run to resume with
> full conversation fidelity, not just a status flag — the full `messages` array the LLM would need,
> serialized to `messages_json`. Design the function itself as a single generator consumed two
> different ways (live SSE, synchronous drain-on-resume) from the start, rather than writing two
> separate implementations that could drift apart.

**Why this matters here specifically**: this is the first PoC in the series where a single logical
operation can genuinely span two unrelated HTTP requests, arbitrarily far apart in time. Getting the
persisted-state shape wrong would only surface as a bug the first time a real approval delay spanned
more than one request — exactly the kind of defect that's expensive to discover late.

## Phase 5 — Frontend: build the design tokens as a system, then verify the display logic reflects the same one truth as the backend

> Define the pastel claymorphism token set (lightness/saturation-targeted palette, the two-directional
> shadow recipe, the 3-way font pairing) before any page component. Separately: when a run can be
> viewed two different ways (live-streaming vs. reopened from History), verify both paths derive any
> displayed number (like a step count) from the *same* source of truth, rather than letting each path
> compute its own.

**Why call this out explicitly**: the live view inventing its own per-card step counter instead of
using the backend's real per-cycle number was a real bug this build shipped and then caught — found
only by placing two of the project's own screenshots side by side and noticing they disagreed on a
number that should have been identical for the same underlying run.

## Phase 6 — Containerize

> Same multi-stage Dockerfile pattern as before — this week needs no seed-corpus or web-search
> connectivity step, so the bootstrap sequence is model-loading only, one step shorter than Compass's.

## Phase 7 — Prove it actually works, including a scenario the automated suite structurally cannot catch

> Write `verify_e2e.py` to include a direct regression test for the guardrail-order bug (calling
> `check_guardrails()` in-process with the exact scenario that would trigger it, not just hoping the
> streaming flow exercises it) and a direct regression test for the stale-run reaper (manufacturing an
> already-stale row rather than waiting 180 real seconds). Separately, accept that some real defects
> — a wrong-but-still-`200`-status display number, an audit column that's silently always zero — are
> invisible to any pass/fail HTTP check by construction, and verify those by actually reading a real
> screenshot or a real API response body, not by trusting a green checkmark.

**Why this matters**: four of this build's six real bugs (everything except the two guardrail-order
findings) were only found this second way — E2E stayed 16/16 the whole time for all of them, because
none of them were the kind of thing an HTTP status code can reveal.

## Phase 8 — Document with facts already in hand, not invented ones

> Write `architecture.md`, `flowchart.md`, and `docs/guide.html` using only facts already
> established — the real `verify_e2e.sh` output across all 4 runs (including the one that hit a real
> external rate limit, reported honestly rather than omitted), the real bootstrap timing measured
> three independent times, the real audit-log entry pulled after fixing the latency bug rather than a
> plausible-sounding invented number.

## General prompting habits used throughout this build

- **Turn "raise the quality" into named, checkable structural deltas** before writing any code — the
  single highest-leverage habit for a request phrased as an ongoing quality bar or a qualitative
  design feeling rather than a concrete spec.
- **Reproduce a claimed reference-code bug by hand before correcting it** — confirms the correction
  is actually correcting something, and gives the regression test something concrete to assert.
- **When two views of the same data can diverge, ask what the single source of truth is** before
  writing either view's rendering logic — the live-vs-reopened step-numbering bug happened precisely
  because this question wasn't asked until after both paths already existed independently.
- **Some real bugs are invisible to automated pass/fail checks by construction** — a wrong display
  number under a "200 OK," an audit column that's silently always zero. Budget real time for reading
  actual screenshots and actual API response bodies, not just trusting a green test suite.
- **Report a real external failure (a rate limit, a flaky dependency) honestly rather than silently
  retrying and moving on** — it's a fact about the build, not a flaw in it, and omitting it would be
  a small but real form of the exact hallucination-by-omission this project's documentation standard
  exists to prevent.
