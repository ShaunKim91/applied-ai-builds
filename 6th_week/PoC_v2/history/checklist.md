# Verity — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| A clear, stated target (the round's core feedback) | A named persona (Dana Whitfield, Senior Claims Research Analyst) and fictional company (Fenwick Mutual) stated explicitly on a public landing page — the first product in this series to have one | `docs/screenshots/00-landing.png`, README |
| A completely different approach from Weeks 1-4 and this project's own prior Compass build | New folder (`PoC_v2`, not an edit to `PoC`), new product name, new design system, new security/observability architecture, a claims-research corpus deliberately never touching live web | Whole `verity/` tree |
| Two connected products, one company | Verity + Threshold share the "Fenwick Ledger" design system (distinct primary accent each) and a documented company narrative — a deliberate departure from "new identity every week," explained in `architecture.md` §3 | `architecture.md` |
| Commercial-grade, not PoC-grade (within local-Docker-only infra) | Organization data model, access+refresh token rotation, CSRF, account lockout, hash-chained audit log, rate limiting, real p50/p95/p99 metrics, structured error log, public status page — see `architecture.md` §4's full checklist and explicit scope boundaries | `backend/app/{security,audit,metrics,rate_limit}.py` |
| Take enough time, no hallucination | 3 real bugs found via direct measurement (not assumed), each with the actual numbers that proved them; fictional legal/regulatory content explicitly labeled as such throughout | `../debug/`, disclaimer banners in-app |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 3 local models (embeddings, reranker, LLM), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ used for opt-in escalation, tested with the real key |
| API key never hardcoded | ✅ file-referenced, read-only volume mount; double-verified clean via wrapped + ground-truth grep |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ config fields present, not called this round |
| Min. 2 AI models | ✅ 4 (embeddings, reranker, local LLM, OpenRouter LLM) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8780 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility test used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.6 GiB container memory at rest; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` |
| Auth + mandatory admin console | ✅ hardened JWT auth; Admin page with Users/Audit Log/Budget/Metrics/Recent Errors/Analytics tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html` |
| Creative unified topic | ✅ "Verity" (truth/verification) for a claims-research assistant, paired with "Threshold" for the guardrailed agent console — one Fenwick Mutual product suite |
| Rigorous, non-hallucinated documentation | ✅ every number in `v1.0.0.md` traces to an actual command run this session; all 3 real bugs documented with their exact measured evidence; fictional legal content explicitly disclosed as such |

## Known coverage gaps (self-identified, not user-reported)

- The entity-hallucination cross-check (`debug/issue-03`) is a partial mitigation, not a full fix —
  a hallucinated single-word or lowercase claim, or a fabricated fact that isn't a named entity
  (e.g. a wrong date or dollar figure), would not be caught by it. Disclosed explicitly in
  `docs/guide.html`'s limitations section rather than presented as solved.
- The rate limiter and metrics store are both single-process, in-memory state — real multi-instance
  deployment would need shared backends (documented in `architecture.md` §4 and §7).
- No onboarding tour/wizard was built — a lower-priority UX item explicitly deferred given the time
  budget, versus the security/observability/grounding-integrity items that were prioritized.
