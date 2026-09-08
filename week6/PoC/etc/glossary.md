# Glossary & Model Cards — Compass

## AI models used

### 1. intfloat/multilingual-e5-small (bi-encoder embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim output) covering 100+ languages in one shared embedding space, requiring a task-specific text prefix (`"query: "` / `"passage: "`) per its model card.
- **Why chosen**: the same embedding model validated in the Week4 "Lucent" PoC — reused here for two roles: reranking live web-search results by cosine similarity, and embedding past research reports so Archive search can find them by meaning.
- **How Compass uses it**: `search/rerank_pipeline.py` embeds the current query and every search result at request time (nothing is pre-indexed, since the source is the live web); `ml/groundedness.py` reuses it to check whether a generated report's sentences resemble the retrieved sources; `routers/research.py`/`routers/archive.py` embed each finished report for later semantic lookup.
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. cross-encoder/ms-marco-MiniLM-L-6-v2 (cross-encoder reranker)
- **What it is**: a MiniLM model fine-tuned on the MS MARCO passage-ranking dataset to jointly score a (query, document) pair — more accurate than a bi-encoder's independent embeddings, at the cost of not being pre-computable.
- **Why chosen**: reused verbatim from the Week2/4 PoCs — and, independently, the same reranker a typical baseline implementation of this pattern actually uses in production (a hash-based toy embedding is sometimes taught as an introductory placeholder, but a real shipped version never uses that shortcut).
- **How Compass uses it**: an opt-in toggle on the Research page (reorders live search results before they're given to the LLM) and the primary comparison axis inside the Grounding Lab page.
- **Card**: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2>

### 3. Qwen/Qwen2.5-0.5B-Instruct (local streaming generation)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: the exact small local LLM validated and reused across the Week1-4 PoCs for fully offline, no-API-key text generation.
- **How Compass uses it**: the default (no-key) provider for both streamed research-report generation and Trend Radar's structured 3-lens extraction.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 4. qwen/qwen3-8b via OpenRouter (optional cloud upgrade, used two ways)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API, supporting OpenAI-compatible SSE streaming (`stream: true`) and OpenRouter's own web-search plugin (`plugins: [{"id": "web"}]`).
- **Why chosen**: cheap (pricing verified live during this project series' Week1 PoC build, reused here), and this project's standing rule that OpenRouter is the only cloud API validated this round — a common reference stack for this pattern (Naver Search API + Gemini) isn't available (no key in this repo's `api_keys/`).
- **How Compass uses it**: (a) an ordinary chat-completion call, strictly opt-in, synthesizing Compass's own retrieved+reranked sources — same mechanism Week4 validated; (b) OpenRouter's fully-managed web-search plugin, a single call that performs live search AND generation server-side, used only inside the Grounding Lab comparison feature and gated by the admin-configured daily budget cap.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b> · Web search feature docs: <https://openrouter.ai/docs/guides/features/plugins/web-search>

### Scaffolded, not validated this round
- **Naver Search API** — this is the search backend a typical baseline implementation of this pattern uses. Named here for attribution/parity, but no key exists in this repo, so Compass uses `ddgs` (free, keyless) as its default search backend instead.
- **Google AI Studio / Gemini** — a typical opt-in LLM-synthesis path in a baseline implementation of this pattern. No key exists in this repo; OpenRouter fills the "smarter, opt-in" role instead.
- **Claude CLI / Codex CLI** — a typical baseline implementation shells out to these as a second opt-in enhancement. Not used here, same reasoning as Week4.
- **OpenAI, Anthropic, direct Gemini API** — config fields exist (`ml/llm.py`), not implemented; calling them raises `NotImplementedError`.

## Key terms

| Term | Meaning in this project |
|---|---|
| **ddgs** | A free, keyless Python client (PyPI package `ddgs`, formerly `duckduckgo-search`) for live web search — Compass's default retrieval source. Its own docs disclose it's unofficial/educational-use software, so `search/web_search.py` treats a failure as expected and falls back to deterministic mock results rather than erroring. |
| **Ghost citation** | A URL a generated report names as a source but which was never actually among the retrieved search results — a sign the model paraphrased or invented a citation instead of grounding strictly in what was searched. A common concept in citation-verification techniques; `ml/ghost_citation.py` implements it as a real, always-on check. |
| **Cost governance / budget cap** | An admin-configurable daily spend limit on OpenRouter's paid web-search calls (`models.BudgetSetting`) — once today's tracked spend would exceed it, the paid call is skipped and the reason is surfaced explicitly, never silently over-spent. This is the standard "budget cap" cost-governance discipline, which a typical baseline implementation of this pattern never implements in code. |
| **Grounding Lab** | Compass's side-by-side comparison of two entire retrieval *strategies* — its own self-hosted search-then-rerank-then-generate pipeline (free) vs. OpenRouter's fully-managed web-search plugin (paid, budget-gated) — one level up from Week4's Retrieval Lab, which only compared two rerankers within one pipeline. |
| **Trend Radar** | A real implementation of a 3-lens (Cost / Security / Approval-friction) tool-evaluation framework: search the web for a topic, then have the LLM extract a structured verdict per lens, honestly returning "Insufficient evidence" rather than guessing when the sources don't support a claim. |
| **RAG (Retrieval-Augmented Generation)** | Retrieving relevant text (here: live web-search results, not a fixed corpus) and giving it to an LLM as context before it answers, so the answer can be grounded in and cited back to real sources. |
| **Bi-encoder vs. cross-encoder** | A bi-encoder embeds the query and each document independently (fast, used for the first-pass ranking of live search results); a cross-encoder scores a query and document jointly (slower, more accurate — used to re-rank just the top candidates). |
| **Groundedness** | Whether a generated report's claims actually trace back to the retrieved sources — checked structurally (`[n]` citation validity) and semantically (per-sentence embedding similarity), reused verbatim from Week4's `ml/groundedness.py`. |
| **Streaming generation** | Returning a model's output incrementally, token by token, instead of waiting for the full response — `transformers.TextIteratorStreamer` (local) and OpenAI-compatible SSE (OpenRouter), both exposed to the browser as Server-Sent-Events-shaped lines. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call is recorded with who made it, which model, how long it took, and whether it succeeded, mirroring the pattern reused from the Week1-4 PoCs. |
