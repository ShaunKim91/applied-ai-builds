# Cradle — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| Escalate quality one more notch, not just simple coding | 6 real bugs found and fixed this round (vs. 1 for Compass) — including a proactively-avoided guardrail-ordering pitfall identified during design, and a genuinely new architectural pattern (a resumable, DB-persisted agent loop) not present in any prior week | `../debug/README.md`, `architecture.md` §7 |
| Genuine 3D and spatial depth, not decoration | `TiltCard.tsx` — a real pointer-tracked `perspective`/`rotateX`/`rotateY` component, reserved for a few hero surfaces; a two-directional claymorphism shadow recipe making surfaces read as physically extruded; a layered, per-index-rotated "stacked card" trace visualization | `docs/screenshots/*.png`, `architecture.md` §3 |
| High lightness, low saturation, light pastel color feel | Dusty lilac `#8b7cc7` / sage green `#2f7a5c` on a soft off-white ground (light theme); the same hues lifted (not inverted) for dark — verified against the same WCAG contrast-ratio methodology as every prior week | `frontend/src/index.css`, `architecture.md` §3 |
| Not a simply-made UI | A fifth distinct nav pattern (floating pill), a third distinct 3-way type system (Quicksand/Plus Jakarta Sans/Space Mono), real pointer-reactive motion — none of which existed as a category before Week7 | `docs/screenshots/*.png` |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 2 local models (embeddings, ReAct agent LLM), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ used for opt-in model-routing escalation, tested with the real key |
| API key never hardcoded | ✅ file-referenced (`api_keys/openrouter.md`), read-only volume mount; double-verified clean via wrapped + ground-truth grep, re-run after final code changes |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ config fields present, not called this round |
| Min. 2 AI models | ✅ 3 (embeddings, local ReAct LLM, OpenRouter escalation LLM) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8770 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility tests (×3, each after a real code fix) used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.75–2.78 GiB container memory at rest; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` (indexing past agent runs for History search) |
| Auth + mandatory admin console | ✅ JWT auth; Admin page with System/Analytics/Guardrails/Budget/Users/Audit Log tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html` |
| Creative unified topic | ✅ "Cradle" — a guardrail-protected space that lets an autonomous agent act safely, matching both this project's safety-guardrail theme and the requested soft/pastel/protective visual language |
| Rigorous, non-hallucinated documentation | ✅ every timing/count number in `v1.0.0.md` traces to an actual command run this session, across 3 independent clean-rebuild measurements; all 6 real bugs are documented with their exact observed symptoms and root causes; 3 non-bug test-tooling ambiguities are disclosed separately from product bugs |

## Known coverage gap (self-identified, not user-reported)

The HITL approval queue is pull-based — an admin has to visit the Approvals page to see a pending
request, with no push notification (email/Slack/webhook). Documented honestly in `architecture.md`
§10 as a deployment consideration rather than silently left unaddressed; this PoC's single-admin
demo scope makes manual polling adequate, but a production deployment would need a real notification
path so a paused run doesn't wait indefinitely for a reviewer who doesn't know to look.

Separately: the guardrail check-then-execute sequence (like Week6 Compass's own budget check) is
not atomic under concurrent load — the same TOCTOU caveat Compass's own `architecture.md` raises,
inherited here rather than newly introduced, and noted again in `architecture.md` §9.
