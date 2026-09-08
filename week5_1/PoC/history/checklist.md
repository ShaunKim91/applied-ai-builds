# Compass — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| Keep raising UI/UX quality every week | Fourth distinct visual identity: navy/brass/teal "chart room," 3-way type system (serif/sans/mono, up from Week4's single font), first dark-default app, a fixed command-console + icon-rail nav (fourth nav pattern), a real motion system (radar-sweep, skeleton shimmer) where Week1-13 had none | `docs/screenshots/*.png`, `architecture.md` §3 |
| Keep raising overall quality every week | New verification axis (ghost-citation checking, generalizing a common introductory technique never implemented in a typical baseline implementation), a governance feature with no precedent in any prior week (cost caps, a standard discipline a typical baseline implementation also never implements), a genuine feature-strategy comparison (Grounding Lab: self-hosted vs. managed) | `architecture.md` §2, `ml/ghost_citation.py`, `models.BudgetSetting` |
| Take enough time, no hallucination | Research agent read the pattern's reference material + a baseline implementation's code + ran its broken example scripts to confirm a real, reproducible import-path bug; 2 external facts (`ddgs`'s API, OpenRouter's web-search plugin shape) verified live via WebFetch before any code was written, not recalled from memory | `plan/v1_plan.md`, this file's own citations |
| Deliver an HTML result to review at the end | `docs/guide.html` (as every prior week) — additionally published as a Claude Artifact this round so it's reachable by a direct link, not just a local file path | Delivered link in the completion report |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 3 local models (embeddings, reranker, LLM), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ used two distinct ways (plain chat completion + managed web search), both tested with the real key |
| API key never hardcoded | ✅ file-referenced (`api_keys/openrouter.md`), read-only volume mount; double-verified clean via wrapped + ground-truth grep |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ config fields present, not called this round |
| Min. 2 AI models | ✅ 4 (embeddings, reranker, local LLM, OpenRouter LLM) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8760 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility test used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.79GiB container memory at rest; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` (here indexing Compass's own past reports, since there's no fixed corpus this week) |
| Auth + mandatory admin console | ✅ JWT auth; Admin page with System/Analytics/Budget/Users/Audit Log tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html` |
| Creative unified topic | ✅ "Compass" — navigating a sea of live information toward a grounded, cited answer ties the UI concept (charts/navigation) directly to the product's core promise |
| Rigorous, non-hallucinated documentation | ✅ every timing/count number in `v1.0.0.md` traces to an actual command run this session; the 1 real bug found is documented with its exact observed malformed output; 2 non-bug test-tooling ambiguities are disclosed separately from product bugs |

## Known coverage gap (self-identified, not user-reported)

Cost-governance's check-then-spend logic (`today_openrouter_spend()` read, then a later `db.commit()`)
is not atomic — a real production deployment under concurrent load could race two simultaneous
requests past the same budget check before either commits. Documented honestly in `architecture.md`
§8 as a deployment consideration rather than silently left unaddressed; this PoC's single-process
demo scope makes the race practically unreachable, but it would need a DB-level atomic reservation
before being trusted in production.
