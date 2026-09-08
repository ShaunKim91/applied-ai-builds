# Glossary & Model Cards — Lucent

## AI models used

### 1. intfloat/multilingual-e5-small (bi-encoder embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim output) covering 100+ languages in one shared embedding space, requiring a task-specific text prefix (`"query: "` / `"passage: "`) per its model card.
- **Why chosen**: a well-established multilingual embedding model, chosen specifically because its multilingual coverage is load-bearing for Lucent's cross-lingual retrieval demonstration (an English and a Korean document on the same topic, retrievable from either language's questions).
- **How Lucent uses it**: embeds every document chunk at indexing time and every question at query time; also reused by `ml/groundedness.py` to check whether a generated answer's sentences actually resemble the retrieved sources.
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. cross-encoder/ms-marco-MiniLM-L-6-v2 (cross-encoder reranker)
- **What it is**: a MiniLM model fine-tuned on the MS MARCO passage-ranking dataset to jointly score a (query, document) pair — more accurate than a bi-encoder's independent embeddings, at the cost of not being pre-computable.
- **Why chosen**: the exact reranker validated in the Week2 PoC's Knowledge Search feature, reused here for the same retrieve-then-rerank pedagogy applied to a document-QA corpus instead of meeting transcripts.
- **How Lucent uses it**: an opt-in toggle both in the Chat page (reorders retrieved chunks before they're given to the LLM) and in the dedicated Retrieval Lab page (shown side by side against the plain bi-encoder ranking).
- **Card**: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2>

### 3. Qwen/Qwen2.5-0.5B-Instruct (local streaming answer generation)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: the exact small local LLM validated and reused across the Week1-3 PoCs for fully offline, no-API-key text generation — here extended to support real token-by-token streaming via `transformers.TextIteratorStreamer`.
- **How Lucent uses it**: the default (no-key) provider for chat answer generation, given the retrieved/reranked source chunks as numbered context.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 4. qwen/qwen3-8b via OpenRouter (optional cloud upgrade)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API, supporting OpenAI-compatible SSE streaming (`stream: true`).
- **Why chosen**: cheap (verified live pricing during the Week1 PoC build, reused here), and the project brief specifically asks for an OpenRouter-validated cloud path this round.
- **How Lucent uses it**: strictly opt-in (a checkbox on the Chat page) alternative to the local model, streamed the same way.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

### Scaffolded, not validated this round
- **OpenAI, Anthropic, Gemini** — config fields exist (`ml/llm.py`), not implemented; calling them raises `NotImplementedError`.

## Key terms

| Term | Meaning in this project |
|---|---|
| **RAG (Retrieval-Augmented Generation)** | Retrieving relevant text from a knowledge base and giving it to an LLM as context before it answers, so the answer can be grounded in and cited back to real sources instead of relying purely on the model's training-time knowledge. |
| **Bi-encoder vs. cross-encoder** | A bi-encoder embeds the query and each document independently (fast, pre-computable — used for the first "retrieve" pass over the whole corpus); a cross-encoder scores a query and document together (slower, more accurate — used to re-rank just the top candidates). |
| **E5 prefixes** | `intfloat/multilingual-e5-small` (and the E5 model family generally) requires prepending `"query: "` to search queries and `"passage: "` to indexed documents before embedding — not optional formatting, it measurably affects retrieval quality. `ml/embeddings.py` bakes this in so callers never have to remember it. |
| **Groundedness** | Whether a generated answer's claims actually trace back to the retrieved sources. Lucent checks this two ways: every `[n]` citation must reference a real retrieved source (structural), and every sentence must be similar enough to at least one retrieved chunk by embedding cosine similarity (content) — see `ml/groundedness.py`. |
| **Streaming generation** | Returning a model's output incrementally, token by token, as it's generated, instead of waiting for the full response — implemented via `transformers.TextIteratorStreamer` (local) and OpenAI-compatible SSE (OpenRouter), both exposed to the browser as Server-Sent-Events-shaped lines over a single `StreamingResponse`. |
| **Word-overlap chunking** | Splitting a long document into passages with some shared words at each boundary, so content spanning a cut point isn't lost to retrieval — the technique validated in the Week2/3 PoCs, applied here (500 words / 50-word overlap) as a real improvement over a naive overlap-free chunker. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call is recorded with who made it, which model, how long it took, and whether it succeeded, mirroring the pattern reused from the Week1-3 PoCs. |
