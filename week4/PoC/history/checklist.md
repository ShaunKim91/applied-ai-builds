# Lucent — Requirements → Implementation Checklist

## This round's explicit new asks

| Ask | Delivered as | Evidence |
|---|---|---|
| UI reflects "transparency" | Glassmorphism design system: `backdrop-filter: blur()` glass panels, 3-layer gradient-mesh background, floating rounded sidebar | `docs/screenshots/*.png`, `docs/guide.html` §UI Differentiation |
| More concise/beautiful/sophisticated than prior rounds | Single-font (Manrope) weight-driven hierarchy, gradient accent, dark-mode background tone shift (not just surface swap) | Same |
| More advanced features | Real token-by-token streaming (local + cloud), multi-turn sessions, groundedness verification, Retrieval Lab bi/cross comparison | `backend/app/ml/llm.py`, `groundedness.py`, `verify_e2e.py` |
| Verification done well | 13-check E2E incl. real streamed-response assembly and a genuine cross-lingual query; run 4 times clean; OpenRouter real-key tested twice; full clean-rebuild test | This file's sibling `v1.0.0.md` |
| Much higher product value than Weeks 10-12 | Dimension-by-dimension comparison against a typical baseline implementation of this pattern (which has **no LLM call at all** by default) | `architecture.md` §2, `docs/guide.html` §Engineering Depth |

## Standing project requirements

| Requirement | Status |
|---|---|
| Local HuggingFace models as primary path | ✅ 3 local models (embeddings, reranker, LLM), zero API keys needed for the default path |
| OpenRouter as the only validated cloud API | ✅ `qwen/qwen3-8b`, tested twice with the real key, both real-answer and correct-refusal cases observed |
| API key never hardcoded | ✅ file-referenced (`api_keys/openrouter.md`), read-only volume mount; double-verified clean via wrapped + ground-truth grep |
| OpenAI/Claude/Gemini scaffolded, unvalidated | ✅ config fields present, not called this round |
| Min. 2 AI models | ✅ 4 (embeddings, reranker, local LLM, OpenRouter LLM) |
| Docker container, auto-detected free port | ✅ `scripts/find_free_port.sh`, defaults from 8750 |
| Containers never deleted in normal operation | ✅ `scripts/stop.sh` uses `docker compose stop`; only this build's own deliberate reproducibility test used `down -v` |
| Shell-script-driven setup/run/model download | ✅ `scripts/{setup,run,stop,verify_e2e,download_data,download_models}.sh` |
| 16GB RAM / CPU-only default target | ✅ measured 2.9-3.1GiB container memory at rest; no GPU used or required |
| SQL + Vector DB | ✅ SQLite + Chroma `PersistentClient` (an explicit improvement over a naive in-memory `Client()`) |
| Auth + mandatory admin console | ✅ JWT auth; Admin page with System/Analytics/Users/Audit Log tabs |
| Bilingual UI | ✅ full KO/EN toggle, frontend + `docs/guide.html` |
| Creative unified topic | ✅ "Lucent" — transparency/light metaphor ties the UI concept to the RAG-groundedness product promise |
| Rigorous, non-hallucinated documentation | ✅ every timing/count number in `v1.0.0.md` traces to an actual command run this session; 3 real bugs documented, 1 real non-bug finding documented honestly |

## Known coverage gap (self-identified, not user-reported)

`verify_e2e.py`'s 13 checks never reload a session's message history after the fact — they only
exercise the live SSE path. This is exactly the class of bug (issue-02) that shipped past all 13
automated checks and was only caught by manual, screenshot-driven testing. Recorded here as an
honest gap rather than silently patched over; a future round could add a 14th check that creates a
session, sends a message, then re-fetches `GET .../messages` and asserts the groundedness object is
present and correctly shaped.
