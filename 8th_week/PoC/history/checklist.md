# Throughline — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| A clear, stated target (the round's core feedback) | A named persona (Marcus Webb, Policyholder Services representative, 50-70 calls/day) stated explicitly on a public landing page | `docs/screenshots/00-landing.png`, README |
| A completely different approach from Weeks 1-7 and this project's own prior products | New product, new mechanism (routed LCEL turns + persisted structured memory, not a ReAct tool loop or a grounded-research pipeline), shared design system with Verity/Threshold | Whole `throughline/` tree |
| Best quality yet — the last product in this round | Real, verified `langchain-core` usage; a genuinely new guardrail axis (memory-write conflicts); redaction at every trust boundary; a real purge/erasure action; 31 E2E checks (more than either sibling); 4 real bugs found and fixed via direct multi-turn testing | `architecture.md`, `../debug/`, `history/v1.0.0.md` |
| Three connected products, one company | Shares Fenwick Mutual and the "Fenwick Ledger" design system with Verity/Threshold (a "ledger ink" indigo as its own primary accent within the shared palette) | `architecture.md` §3 |
| Commercial-grade, not PoC-grade (within local-Docker-only infra) | Organization data model, access+refresh token rotation, CSRF, account lockout, hash-chained audit log, rate limiting, real p50/p95/p99 metrics — identical security architecture to Verity/Threshold, reused verbatim (the third time is a deliberate platform decision, not a shortcut) | `backend/app/{security,audit,metrics,rate_limit}.py` |
| Take enough time, no hallucination | The real `langchain-core` API was verified against the actual installed package (catching a real deprecation, `RunnableWithMessageHistory`) before any code was written against it; the local model's actual behavior was empirically tested before finalizing prompts; a common introductory claim (`ast.literal_eval` as an `eval()` fix) was independently verified and found incomplete | `architecture.md` §5, `../prompts/vibe_coding_prompts.md` |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 2 local models (embeddings, the shared LCEL Runnable), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ used for opt-in escalation, tested with the real key |
| API key never hardcoded | ✅ file-referenced, read-only volume mount; double-verified clean via wrapped + ground-truth grep, including after the completed `docs/guide.html` was added |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ same pattern as Verity/Threshold's config fields (present, not called this round) |
| Min. 2 AI models | ✅ 3 (embeddings, the shared local LCEL Runnable, OpenRouter escalation) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8800 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility tests (×3) used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.53–3.04 GiB container memory across idle and load states; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` |
| Auth + mandatory admin console | ✅ hardened JWT auth; Admin page with Memory/Conflicts/Retention/Users/Audit Log/Budget/Metrics/Errors/Analytics tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html`, i18n key parity verified (96/96) |
| Creative unified topic | ✅ "Throughline" (a thread that connects every call — memory/continuity) completing the trio with "Verity" (truth) and "Threshold" (a safety boundary) — one Fenwick Mutual product suite |
| Rigorous, non-hallucinated documentation | ✅ every number in `v1.0.0.md` traces to an actual command run this session, across clean-rebuild measurements; all 4 real bugs are documented with their exact captured symptoms, not paraphrased summaries |

## Known coverage gaps (self-identified, not user-reported)

- Redaction is regex pattern-based, not a certified PII-detection engine — known false negatives for
  free-text names, addresses, and indirect identifiers, stated explicitly in `docs/guide.html` rather
  than implied away.
- The purge/right-to-erasure action deletes this application's own rows and records an audit entry,
  but cannot retract anything already sent to the OpenRouter escalation path during a case's lifetime.
- The 0.5B local model occasionally addresses the caller by name directly in a reply meant for the
  representative, despite an explicit system-prompt instruction not to — a known small-model
  instruction-following limitation (see `etc/glossary.md`), not corrected further this round since the
  facts it relays stayed accurate across every test run.
- The structured-output tool router's bounded retry does not always recover a malformed first attempt
  (measured directly, not assumed) — the honest fallback (a direct reply, never a silent guess) is the
  mitigation, not a claim of near-perfect routing reliability.
- The memory-write conflict guardrail is scoped to the four extracted fields (`caller_name`,
  `policy_number`, `preferred_callback_window`, `topic`) — it does not generalize to arbitrary
  free-text case notes, which this product does not currently support as a distinct data type.
