# Issue 03 — Real LCEL composition crashed the first time summarization actually ran

**Severity**: High (crashed the window-to-summary transition outright — the second half of this
build's dual-strategy memory claim)
**Status**: Fixed, regression-tested (`verify_e2e.py::step_window_summary_transition`)

## Symptom (actually observed, real traceback)

The first real conversation long enough to overflow the live window (forced via a lowered
`window_turns=1` admin setting to reach it quickly) crashed on the turn that should have triggered
summarization:

```
TypeError: 'ChatPromptValue' object is not subscriptable
```

raised from `chains/llm_runnable.py::_split_system()` at `messages[0]`.

## Root cause

`chains/memory_store.py`'s `_summary_chain = SUMMARY_PROMPT | local_llm | StrOutputParser()` pipes a
real `ChatPromptTemplate` directly into `local_llm` (the `RunnableLambda` wrapping this app's local
generation function). LangChain's LCEL `|` composition invokes `SUMMARY_PROMPT.invoke(...)` first and
hands its *return value* — a `ChatPromptValue` object — to the next step, not a plain
`list[BaseMessage]`. `ChatPromptValue` is not subscriptable, so `generate_reply()`'s naive
`messages[0]` check failed immediately.

This was never hit by `chains/router.py` or `chains/extraction.py`, both of which build a
`list[BaseMessage]` by hand and pass it straight to `local_llm` with no `ChatPromptTemplate` in front
of it — a genuinely different LCEL composition shape, only exercised once summarization itself was
actually exercised (which needs a long-enough real conversation, not just a router/extraction call).

## Fix

`chains/llm_runnable.py::_split_system()` now normalizes its input first: `if hasattr(messages,
"to_messages"): messages = messages.to_messages()` before the `isinstance(messages[0], SystemMessage)`
check. `generate_reply()`, `stream_reply()`, and the `local_llm` Runnable all funnel through this same
normalization, so any future LCEL chain that pipes a `ChatPromptTemplate` directly into `local_llm`
(rather than building a plain message list) is handled correctly too, not just this one call site.

## How this was found

Direct manual testing of the window-to-summary transition specifically — deliberately forced by
lowering `window_turns` via the admin API and sending enough turns to overflow it, rather than waiting
for a long organic conversation. This mirrors this project's own standing practice of testing the
LCEL composition shapes actually used (a `ChatPromptTemplate`-fronted chain, not just a hand-built
message list) rather than assuming "the router/extraction chains work, so the identically-wrapped
Runnable must work everywhere."
