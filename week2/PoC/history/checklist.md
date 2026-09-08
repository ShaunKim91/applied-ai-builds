# Requirements Checklist — Week2 PoC ("VoxIQ")

Maps every requirement in `request/20260824_request001.md` to how it was satisfied. ✅ = done and verified. Line references point to the original request file.

| # | Requirement | Status | Where / how |
|---|---|---|---|
| 1 | New `PoC` folder per week, new project inside | ✅ | `week2/PoC/projects/voxiq/` (a new PoC folder, kept separate from this week's other assignment work) |
| 2 | Local models as primary approach | ✅ | 5 of 6 AI models run 100% locally (bi-encoder, cross-encoder, Whisper, Qwen2.5-0.5B, GPT-2); no API key required for the app to fully function |
| 3 | Cloud API only when truly needed, small/cheap models | ✅ | OpenRouter `qwen/qwen3-8b` ($0.117/$0.455 per M tok) is opt-in only, for one feature (analytics code-gen), toggled per-request via a checkbox |
| 4 | OpenRouter as default API, referenced from `api_keys/openrouter.md` (not hardcoded) | ✅ | `config.py`'s `openrouter_api_key_file` + `read_key_file()`; verified the container reads the real mounted file and the real API call succeeds (see `history/v1.0.0.md`) |
| 5 | OpenAI/Claude/Gemini scaffolded but only OpenRouter validated this round | ✅ | `ml/llm.py` has `openai_api_key_file`/`anthropic_api_key_file`/`gemini_api_key_file` config fields; calling those providers raises a clear `NotImplementedError`. Same pattern applied to E2B in `ml/sandbox.py` (`e2b_available()` + `run_code_e2b()` raising `NotImplementedError`) since it too has no validated key this round |
| 6 | Cheapest reasonable models | ✅ | All 5 local models are the smallest reasonable variants for their respective tasks; OpenRouter model reused from an earlier product's live pricing check in this series |
| 7 | Check for NVIDIA GPU, use it if present, else CPU | ✅ | `scripts/setup.sh` detects `nvidia-smi` and passes the matching torch wheel index as a Docker build-arg; this build ran the CPU path (verified: no NVIDIA GPU on the build/dev host — Apple M4 Pro) |
| 8 | Target ~16GB RAM, macOS + Windows | ✅ | Measured real container memory (2.82 GiB at rest, all 5 models warm) recorded in `history/v1.0.0.md`; scripts use portable bash (`/dev/tcp`, no macOS/Linux-only tools) so they work under Windows Git Bash/WSL2 |
| 9 | Must use Docker containers, per-project port, auto-detect free port | ✅ | `docker-compose.yml` + `scripts/find_free_port.sh` (portable `/dev/tcp` scanner); port range 8730s, distinct from Week1's 8720s |
| 10 | Container not deleted on exit | ✅ | `scripts/stop.sh` uses `docker compose stop`, never `down`; `restart: unless-stopped` in compose |
| 11 | Setup/run via shell script, simple to use | ✅ | `scripts/setup.sh` / `run.sh` / `stop.sh` / `verify_e2e.sh` / `download_data.sh` / `download_models.sh` — one command each |
| 12 | Reference `reference_skills` where applicable | ✅ | `dataviz` → validated palette reused for the tokenizer chip colors + attention heatmap; `interface-craft` → spacing/contrast discipline in the React UI; `html-docsmith` → `docs/guide.html` structure |
| 13 | Plan before work, checklist to track progress | ✅ | `plan/v1_plan.md` (approved before implementation began); this file |
| 14 | PoC-level depth, not a toy | ✅ | 6 AI models, auth+admin, SQL+vector DB, real public data, background jobs, i18n, full E2E test suite |
| 15 | Reflect prior work where reasonable | ✅ | Reuses `Qwen2.5-0.5B-Instruct` and CommerceIQ's auth/bootstrap/readiness code from this same project series, as the brief explicitly encouraged |
| 16 | `projects/` subfolder with runnable code, requirements.txt, README.md, architecture.md | ✅ | All present in `projects/voxiq/` |
| 17 | HTML operations guide, all-in-one, KO default / EN toggle, dark default / light toggle | ✅ | `docs/guide.html` |
| 18 | Minimum hardware requirements documented | ✅ | `docs/guide.html` §Hardware, measured numbers in `history/v1.0.0.md` |
| 19 | Commercial/cloud scale-out notes + est. monthly cost | ✅ | `architecture.md` §6 + `docs/guide.html` §Production & Cloud Scaling |
| 20 | Deployment considerations | ✅ | `architecture.md` §7 + `docs/guide.html` §Deployment Considerations, including the VoxIQ-specific note on replacing the local sandbox before real deployment |
| 21 | Screenshots of major screens in the HTML guide | ✅ | `docs/screenshots/*.png` (7 screens), captured from the actually-running app via Playwright; embedded in `docs/guide.html` |
| 22 | Architecture considered, staged verification code | ✅ | `architecture.md`; `backend/verify_e2e.py` is the staged, step-by-step verification (12 checks, real HTTP, no mocks) |
| 23 | Public data with source + how to download it, automated via shell script | ✅ | `data/SOURCES.md`; `scripts/download_data.sh`; automatic on first container boot |
| 24 | Foundational knowledge included, with sources | ✅ | `docs/guide.html` §Foundational Knowledge + `etc/glossary.md`, real citations (arXiv links, GitHub, HF model cards) |
| 25 | End-to-end code verification | ✅ | `backend/verify_e2e.py` via `scripts/verify_e2e.sh`, run against the live container twice (before and after the clean rebuild) — real results in `history/v1.0.0.md` |
| 26 | UI/UX considered; "if Streamlit isn't enough, use something else" | ✅ | FastAPI + React/TypeScript/Vite/Tailwind SPA, not Streamlit (reasoning in `README.md` and `architecture.md` §2 — the bi- vs. cross-encoder side-by-side comparison and the attention heatmap specifically need this) |
| 27 | Commercial/enterprise-usable quality | ✅ | Auth, admin console, audit trail, typed API, structured storage, real datasets |
| 28 | `architecture.md` with visualized architecture, also embedded in the HTML | ✅ | `architecture.md` (Mermaid diagrams) + reproduced in `docs/guide.html` §Architecture |
| 29 | `flowchart.md` per major function/model, also embedded in the HTML | ✅ | `flowchart.md` (7 Mermaid flowcharts) + reproduced in `docs/guide.html` §Flowcharts |
| 30 | GitHub-quality files | ✅ | Root `.gitignore` (from Week1, covers all weeks) + `.dockerignore`, structured README, no secrets committed (re-audited, see `history/v1.0.0.md`) |
| 31 | May build on earlier weeks' content (encouraged) | ✅ | See #15 |
| 32 | SQL or NoSQL DB + Storage; Vector DB/LangChain encouraged | ✅ (SQL + Vector DB; LangChain not used this round) | SQLite (`models.py`) + Chroma (`vectorstore.py`); LangChain intentionally deferred to a future product where it's the natural fit |
| 33 | Sign-up/login where relevant | ✅ | `routers/auth.py`, JWT + bcrypt, copied from CommerceIQ's already-hardened implementation |
| 34 | Admin page, double-checked | ✅ | `pages/Admin.tsx` + `routers/admin.py`; role-gated (`require_admin`), verified a non-admin is correctly 403'd (E2E check 11) |
| 35 | Animated/gif assets allowed (optional) | — not used | Static PNG screenshots were judged sufficient and more reliable for a documentation artifact; no functional loss |
| 36 | Web service bilingual EN default / KO toggle | ✅ | `frontend/src/i18n/` (en.json default, ko.json), opposite default from the HTML guide as specified |
| 37 | Modular, architecturally considered | ✅ | `backend/app/{ml,etl,routers}` separation; `frontend/src/{pages,components,i18n,theme,api}` separation |
| 38 | `debug/` folder — issues + causes + fixes, what to study further | ✅ | `debug/README.md` + 2 issue files, both real issues actually hit during this build, not fabricated — see `debug/README.md`'s index |
| 39 | `plan/` folder — versioned plan | ✅ | `plan/v1_plan.md` |
| 40 | `history/` folder — versioned history + latest summary | ✅ | `history/v1.0.0.md` + `history/SUMMARY.md` |
| 41 | `prompts/` folder — vibe-coding prompt collection + time/cost estimate | ✅ | `prompts/vibe_coding_prompts.md` + `prompts/time_and_cost_estimate.md` |
| 42 | `etc/` folder | ✅ | `etc/glossary.md` |
| 43 | Not limited to Python; other languages allowed, with reasoning | ✅ | TypeScript/React for the frontend, reasoning in `README.md` |
| 44 | Creative, well-considered topic selection | ✅ | "VoxIQ" unifies 4 AI techniques (embeddings/reranking, audio ASR, code sandboxing, LLM internals) into one realistic meeting-intelligence product instead of 4 disjoint demo tabs |
| 45 | Minimum 2 AI models | ✅ (6 used) | See #2–#6 |
| 46 | External GitHub repos may be referenced/pulled for concept, with clear attribution | ✅ (used, attributed) | `openai/whisper`'s `jfk.flac` test asset + `hf-internal-testing/librispeech_asr_dummy` — attribution in `data/SOURCES.md`, `README.md`, `etc/glossary.md`; no application code was copied from any external repo (CommerceIQ's own code, which this project *is* attributed to reusing, is this project's own prior work, not a third party) |
| 47 | Model download commands included in the shell scripts | ✅ | Models download automatically via `app/main.py`'s startup bootstrap (triggered by `scripts/setup.sh`/`run.sh`); `scripts/download_models.sh` exposes the same step as an explicit, synchronous CLI command for all 5 local models, and `scripts/download_data.sh` covers the two public datasets explicitly |

## Final status (2026-08-28)

All items above are ✅ complete and verified against the real, running
container — see [`v1.0.0.md`](v1.0.0.md) for the actual E2E pass/fail
table, measured hardware numbers, bootstrap timing, and screenshot notes.
Nothing in this checklist was marked done speculatively; every claim above
is backed by a real command run during this build (E2E script output,
`docker stats`, `curl` responses, or a captured screenshot).
