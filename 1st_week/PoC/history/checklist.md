# Requirements Checklist — PoC ("CommerceIQ")

Maps every requirement in `request/20260824_request001.md` to how it was satisfied. ✅ = done and verified. Line references point to the original request file.

| # | Requirement | Status | Where / how |
|---|---|---|---|
| 1 | New `PoC` folder per week, new project inside | ✅ | `1st_week/PoC/projects/commerceiq/` |
| 2 | Local models as primary approach | ✅ | 4 of 5 AI models run 100% locally (ViT-tiny, tiny-sd, e5-small, Qwen2.5-0.5B); no API key required for the app to fully function |
| 3 | Cloud API only when truly needed, small/cheap models | ✅ | OpenRouter `qwen/qwen3-8b` ($0.117/$0.455 per M tok) is opt-in only, for one feature (forecast narrative upgrade), toggled per-request by the user |
| 4 | OpenRouter as default API, referenced from `api_keys/openrouter.md` (not hardcoded) | ✅ | `config.py`'s `openrouter_api_key_file` + `read_key_file()`; verified the container reads the real mounted file and the real API call succeeds (see `history/v1.0.0.md`) |
| 5 | OpenAI/Claude/Gemini scaffolded but only OpenRouter validated this round | ✅ | `ml/llm.py` has `openai_api_key_file`/`anthropic_api_key_file`/`gemini_api_key_file` config fields; calling those providers raises a clear `NotImplementedError` rather than silently pretending to work |
| 6 | Cheapest reasonable models | ✅ | All 4 local models are the smallest well-established variants for their task; OpenRouter model chosen specifically for low price after a live pricing check |
| 7 | Check for NVIDIA GPU, use it if present, else CPU | ✅ | `scripts/setup.sh` detects `nvidia-smi` and passes the matching torch wheel index as a Docker build-arg; this build ran the CPU path (verified: no NVIDIA GPU on the build/dev host) |
| 8 | Target ~16GB RAM, macOS + Windows | ✅ | Measured real container memory usage recorded in `history/v1.0.0.md`; scripts use portable bash (`/dev/tcp`, no macOS/Linux-only tools) so they work under Windows Git Bash/WSL2 |
| 9 | Must use Docker containers, per-project port, auto-detect free port | ✅ | `docker-compose.yml` + `scripts/find_free_port.sh` (portable `/dev/tcp` scanner, no `lsof`/`nc` dependency) |
| 10 | Container not deleted on exit | ✅ | `scripts/stop.sh` uses `docker compose stop`, never `down`; `restart: unless-stopped` in compose |
| 11 | Setup/run via shell script, simple to use | ✅ | `scripts/setup.sh` / `run.sh` / `stop.sh` / `verify_e2e.sh` / `download_data.sh` — one command each |
| 12 | Reference `reference_skills` where applicable | ✅ | `html-docsmith` → `docs/guide.html` structure/tokens; `interface-craft` → spacing/contrast/token discipline in the React UI; `dataviz` → validated palette + chart form for the forecast chart; `global-correspondence` → bilingual register awareness (informal note: Korean copy kept consistent register) |
| 13 | Plan before work, checklist to track progress | ✅ | `plan/v1_plan.md` (approved before implementation began); this file |
| 14 | PoC-level depth, not a toy | ✅ | 5 AI models, auth+admin, SQL+vector DB, real public data, background jobs, i18n, full E2E test suite |
| 15 | Reflect prior weeks' content where reasonable | ✅ | Reuses `intfloat/multilingual-e5-small` and `Qwen2.5-0.5B-Instruct`, both well-established choices for this project series, as the brief explicitly encouraged |
| 16 | `projects/` subfolder with runnable code, requirements.txt, README.md, architecture.md | ✅ | All present in `projects/commerceiq/` |
| 17 | HTML operations guide, all-in-one, KO default / EN toggle, dark default / light toggle | ✅ | `docs/guide.html` |
| 18 | Minimum hardware requirements documented | ✅ | `docs/guide.html` §Hardware, measured numbers in `history/v1.0.0.md` |
| 19 | Commercial/cloud scale-out notes + est. monthly cost | ✅ | `architecture.md` §5 + `docs/guide.html` §Production & Cloud Scaling |
| 20 | Deployment considerations | ✅ | `architecture.md` §6 + `docs/guide.html` §Deployment Considerations |
| 21 | Screenshots of major screens in the HTML guide | ✅ | `docs/screenshots/*.png`, captured from the actually-running app via Playwright; embedded in `docs/guide.html` |
| 22 | Architecture considered, staged verification code | ✅ | `architecture.md`; `backend/verify_e2e.py` is the staged, step-by-step verification (12 checks, real HTTP, no mocks) |
| 23 | Public data with source + how to download it, automated via shell script | ✅ | `data/SOURCES.md`; `scripts/download_data.sh`; automatic on first container boot |
| 24 | Foundational knowledge included, with sources | ✅ | `docs/guide.html` §Foundational Knowledge + `etc/glossary.md`, real citations (arXiv links, journal names) |
| 25 | End-to-end code verification | ✅ | `backend/verify_e2e.py` via `scripts/verify_e2e.sh`, run against the live container — real results in `history/v1.0.0.md` |
| 26 | UI/UX considered; "if Streamlit isn't enough, use something else" | ✅ | FastAPI + React/TypeScript/Vite/Tailwind SPA, not Streamlit (reasoning in `README.md` and `architecture.md` §2) |
| 27 | Commercial/enterprise-usable quality | ✅ | Auth, admin console, audit trail, typed API, structured storage, real datasets |
| 28 | `architecture.md` with visualized architecture, also embedded in the HTML | ✅ | `architecture.md` (Mermaid diagrams) + reproduced in `docs/guide.html` §Architecture |
| 29 | `flowchart.md` per major function/model, also embedded in the HTML | ✅ | `flowchart.md` (7 Mermaid flowcharts) + reproduced in `docs/guide.html` §Flowcharts |
| 30 | GitHub-quality files | ✅ | `.gitignore`, `.dockerignore`, structured README, no secrets committed |
| 31 | May build on earlier weeks' content (encouraged) | ✅ | See #15 |
| 32 | SQL or NoSQL DB + Storage; Vector DB/LangChain encouraged | ✅ (SQL + Vector DB; LangChain not used here) | SQLite (`models.py`) + Chroma (`vectorstore.py`); LangChain intentionally deferred to a later product in this series to avoid diluting this PoC's focus — noted here rather than silently omitted |
| 33 | Sign-up/login where relevant | ✅ | `routers/auth.py`, JWT + bcrypt |
| 34 | Admin page, double-checked | ✅ | `pages/Admin.tsx` + `routers/admin.py`; role-gated (`require_admin`), verified a non-admin is correctly 403'd (see E2E step 10) |
| 35 | Animated/gif assets allowed (optional) | — not used | Static PNG screenshots were judged sufficient and more reliable for a documentation artifact; no functional loss |
| 36 | Web service bilingual EN default / KO toggle | ✅ | `frontend/src/i18n/` (en.json default, ko.json), opposite default from the HTML guide as specified |
| 37 | Modular, architecturally considered | ✅ | `backend/app/{ml,etl,routers}` separation; `frontend/src/{pages,components,i18n,theme,api}` separation |
| 38 | `debug/` folder — issues + causes + fixes, pointers to underlying concepts, what to study further | ✅ | `debug/README.md` + 7 issue files (`issue-01` through `issue-07`), every one a real issue actually hit during this build, not fabricated — see `debug/README.md`'s index |
| 39 | `plan/` folder — versioned plan | ✅ | `plan/v1_plan.md` |
| 40 | `history/` folder — versioned history + latest summary | ✅ | `history/v1.0.0.md` + `history/SUMMARY.md` |
| 41 | `prompts/` folder — vibe-coding prompt collection + time/cost estimate | ✅ | `prompts/vibe_coding_prompts.md` + `prompts/time_and_cost_estimate.md` |
| 42 | `etc/` folder | ✅ | `etc/glossary.md` |
| 43 | Not limited to Python; other languages allowed, with reasoning | ✅ | TypeScript/React for the frontend, reasoning in `README.md` |
| 44 | Creative, well-considered topic selection | ✅ | "CommerceIQ" unifies 3 AI techniques into one realistic commerce-ops product instead of 3 disjoint demo tabs |
| 45 | Minimum 2 AI models | ✅ (5 used) | See #2–#6 |
| 46 | External GitHub repos may be referenced/pulled for concept, with clear attribution | ✅ (used, attributed) | GroceryStoreDataset (MIT, Klasson et al.) — attribution in `data/SOURCES.md`, `README.md`, `etc/glossary.md`; no application code was copied from any external repo |
| 47 | Model download commands included in the shell scripts | ✅ | Models download automatically via `app/main.py`'s startup bootstrap (triggered by `scripts/setup.sh`/`run.sh`); `scripts/download_models.sh` exposes the same step as an explicit, synchronous CLI command (added after a follow-up review confirmed all 4 models load correctly via it), and `scripts/download_data.sh` covers the two public datasets explicitly |

## Final status (2026-08-24, re-verified 2026-08-28)

All items above are ✅ complete and verified against the real, running container — see [`v1.0.0.md`](v1.0.0.md) for the actual E2E pass/fail table, measured hardware numbers, and screenshot notes, and [`v1.0.1.md`](v1.0.1.md) for a follow-up security audit and documentation review that found and fixed a few more real issues (a repo-root secret-exposure gap, a broken doc link, an `run.sh` bug). Nothing in this checklist was marked done speculatively; every claim above is backed by a real command run during this build (E2E script output, `docker stats`, `curl` responses, or a captured screenshot).
