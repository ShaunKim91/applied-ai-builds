# Issue 01 — chromadb posthog telemetry error on every collection call

## Symptom

Real log output from the running container (captured during the live E2E
verification run):

```
2026-08-23 20:55:34,439 [ERROR] chromadb.telemetry.product.posthog: Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
2026-08-23 20:55:34,447 [ERROR] chromadb.telemetry.product.posthog: Failed to send telemetry event ClientCreateCollectionEvent: capture() takes 1 positional argument but 3 were given
```

## Root cause

`chromadb`'s anonymous-usage-telemetry module calls into the `posthog`
Python package with a call signature (`capture(distinct_id, event, ...)`)
that doesn't match the `posthog` version resolved by `pip` in this build
(`requirements.txt` pins `chromadb>=0.5,<1.0` but does not pin `posthog`
directly, so pip picked the latest compatible `posthog` release, which
changed `capture()`'s signature). This is a known upstream version-skew bug
between chromadb and posthog, not a bug in CommerceIQ's own code.

## Impact

**None on functionality.** This is chromadb's *outbound anonymous telemetry
ping to PostHog* failing — it has nothing to do with storing or querying
vectors. `vectorstore.py`'s actual `upsert()`/`query()` calls succeeded in
every test (confirmed via the live E2E run and the semantic search feature
working correctly end-to-end). The error is logged and swallowed internally
by chromadb itself; it never propagates to CommerceIQ's request handlers.

## Fix applied

None needed for correctness. For a quieter log, a real deployment could set
the environment variable `ANONYMIZED_TELEMETRY=False` (chromadb's documented
opt-out flag) before starting the process, which skips the PostHog call
entirely. This PoC leaves telemetry as-is (chromadb's default) since it does
not affect behavior and this is a self-hosted, non-production instance.

## What to study if this is new to you

- This is a good concrete example of **why `vectorstore.py` wraps chromadb
  in a try/except fallback** (the "안전 파싱 / try-except 방어적 패턴"
  — a defensive `safe_json`-style pattern — and the general "mock-first /
  fail gracefully" philosophy used consistently across this project series)
  — a third-party library's internal, non-critical failure should never be
  allowed to become YOUR application's failure.
- Background: chromadb's own docs describe this exact fallback-to-pure-
  Python-cosine pattern for when the optional native backend isn't
  available, which is exactly the defensive pattern this project's
  `vectorstore.py` reuses.
