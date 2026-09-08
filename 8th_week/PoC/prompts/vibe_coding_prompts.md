# Vibe-Coding Prompt Playbook — Throughline (Week8 PoC)

The third product in the Fenwick Mutual suite, and the first built entirely fresh (no predecessor PoC
existed for Week8). This playbook covers what was specific to this build — reusing a proven
platform layer for the third time, verifying a fast-moving library's real API before depending on it,
and letting direct empirical testing of the real local model shape the design rather than assuming a
plan survives contact with reality.

## Phase 0 — Reuse a proven platform layer a THIRD time, deliberately

> Before writing any Throughline-specific code, copy `security.py`, `audit.py`, `rate_limit.py`,
> `metrics.py`, and `database.py` from Threshold verbatim — these are product-agnostic infrastructure,
> already proven twice over. Design only what's genuinely new: the data model and the domain logic.

**Why**: by the third product in one company's suite, this is no longer "reuse because it's
convenient" — it's the correct engineering call. A real internal tool family sharing one auth/audit/
observability platform layer, rather than each app reinventing its own, is itself a commercial-grade
signal. What's genuinely new in this build lives entirely in `chains/` and the domain tables.

## Phase 1 — Verify a library's real current API before depending on it, not from memory

> Before writing any `chains/` code, install the actual `langchain-core` version this build will pin,
> and directly test the exact APIs the plan calls for — `RunnableWithMessageHistory`,
> `BaseChatMessageHistory`, `trim_messages`, `PydanticOutputParser`, `RunnableLambda` — against real
> smoke-test calls, not assumed behavior from training data.

**Why**: this caught something training-data familiarity would have missed entirely —
`RunnableWithMessageHistory` (the "obviously correct" idiomatic choice for LangChain memory) emits
`LangChainPendingDeprecationWarning: ... Use LangGraph's built-in persistence instead` on the actual
currently-installed release. Shipping new code on a component the library itself flags for removal
would have been a real, avoidable engineering smell — caught only because the plan was verified
against the real package instead of assumed correct from familiarity with the API's older shape.

## Phase 2 — Test the real local model's actual behavior before finalizing a design decision

> Before writing the reply-composition or tool-routing prompts, load the real
> `Qwen/Qwen2.5-0.5B-Instruct` model in a scratch environment and run the exact kind of multi-turn,
> tool-mixed conversation the product will actually have — measure what breaks, not what an assumed,
> differently-shaped prior fix implies should work.

**Why**: the plan's own working assumption — reuse a known tuned system prompt to avoid regressing a
documented "forgets the caller's name" bug — turned out to be untestable as stated, because that prior
fix was validated only in Korean, for a product this build was building in English. Direct testing
surfaced a DIFFERENT, more relevant failure mode for this architecture: the model claiming "I don't
have tool access" and second-guessing a tool result already handed to it in the prompt. The system
prompt that was actually shipped was independently designed and iteratively tested against real
output, not translated from anywhere else. The same direct-testing discipline, applied to the
structured-output tool router, produced a real measured statistic (2 of 6 realistic test messages
succeeded on the first attempt) instead of an assumed one — see `debug/README.md`.

## Phase 3 — Direct manual multi-turn testing found more real bugs than the automated suite would have on its own

> After the core mechanism works in isolation, run real multi-turn conversations through the actual
> orchestrator end-to-end — not just unit-level chain calls — before writing the E2E regression suite.
> Then write the suite's steps FROM what direct testing found, not from what seemed likely to break.

**Why**: four real, distinct bugs surfaced this way, none of which a first-draft `verify_e2e.py`
written from the plan alone would likely have anticipated: a session-lifetime bug only visible once a
memory conflict organically occurred across the SSE generator's session boundary; structured memory
being extracted and persisted but never actually reaching the reply prompt (the feature not doing its
one job, despite every individual piece working); an LCEL composition shape
(`ChatPromptTemplate | Runnable`) that only the summarization chain used, crashing the first time a
long-enough conversation actually triggered it; and a silent matching gap between a caller's natural
"morning"/"afternoon" phrasing and a fixed `"...AM"`/`"...PM"`-stamped slot table. All four are now
named regression steps in `verify_e2e.py`, written after each fix, per this project's own standing
practice.

## General prompting habits used throughout this build

- **The third time a platform layer is needed, reuse it — don't redesign it "because this is a new
  product."** Novelty belongs in the domain logic, not the auth/audit/observability foundation.
- **A fast-moving library's API from training data can be stale — verify the specific calls a plan
  depends on against the actual installed version before writing code around them.**
- **A prior build's fix, validated in a different language or a differently-shaped architecture, is a
  starting hypothesis, not a guarantee — test the actual shape this build will ship, not the shape a
  sibling build already proved.**
- **Persisting something and a system actually USING it are two different claims — test the end-to-end
  behavior a feature is supposed to enable, not just that its own write path succeeds.**
- **Write the E2E suite's regression steps from what real testing found, not from what seemed likely
  to break** — this is how all four of this build's real bugs became permanent regression coverage
  rather than one-off fixes nothing would catch if they recurred.
