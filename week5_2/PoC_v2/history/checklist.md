# Threshold — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| A clear, stated target (the round's core feedback) | A named persona (Priya Nakamura, Claims Processing Team Lead) stated explicitly on a public landing page | `docs/screenshots/00-landing.png`, README |
| A completely different approach from Weeks 10-13 and this project's own prior Cradle build | New folder (`PoC_v2`), new product name, shared design system with Verity, amount-aware HITL redesign, a claims-processing tool set | Whole `threshold/` tree |
| Two connected products, one company | Shares Fenwick Mutual and the "Fenwick Ledger" design system with Verity (copper as its own primary accent within the shared palette) | `architecture.md` §3 |
| Commercial-grade, not PoC-grade (within local-Docker-only infra) | Organization data model, access+refresh token rotation, CSRF, account lockout, hash-chained audit log, rate limiting, real p50/p95/p99 metrics — identical security architecture to Verity, applied to the agent-console domain | `backend/app/{security,audit,metrics,rate_limit}.py` |
| Take enough time, no hallucination | 1 real bug (two manifestations) found via direct trace inspection, with the actual captured malformed strings quoted in the write-up | `../debug/` |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 2 local models (embeddings, ReAct agent LLM), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ used for opt-in escalation, tested with the real key |
| API key never hardcoded | ✅ file-referenced, read-only volume mount; double-verified clean via wrapped + ground-truth grep |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ config fields present, not called this round |
| Min. 2 AI models | ✅ 3 (embeddings, local ReAct LLM, OpenRouter escalation LLM) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8790 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility tests (×3) used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.53–2.58 GiB container memory at rest; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` |
| Auth + mandatory admin console | ✅ hardened JWT auth; Admin page with Guardrails/Users/Audit Log/Budget/Metrics/Recent Errors/Analytics tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html` |
| Creative unified topic | ✅ "Threshold" (an agent that knows when to stop and ask) paired with "Verity" (truth/verification) — one Fenwick Mutual product suite |
| Rigorous, non-hallucinated documentation | ✅ every number in `v1.0.0.md` traces to an actual command run this session, across 3 independent clean-rebuild measurements; the real bug is documented with its exact captured trace text |

## Known coverage gaps (self-identified, not user-reported)

- The HITL approval queue is pull-based — an admin has to visit the Approvals page, with no push
  notification. Same gap as Verity's own architecture, documented honestly rather than silently
  left unaddressed.
- `close_and_purge_claim_file` is a decoy tool never reachable in normal operation (never in
  `ALLOWED_TOOLS`) — by design, not a gap, but noted here for completeness since it exists in the
  codebase without a UI path to it.
- The guardrail check-then-execute sequence is not atomic under concurrent load — the same TOCTOU
  caveat every prior PoC in this project series (including Verity) shares.
