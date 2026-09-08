# Glossary & Model Cards — VoxIQ

## AI models used

### 1. sentence-transformers/all-MiniLM-L6-v2 (bi-encoder)
- **What it is**: a 6-layer MiniLM sentence-embedding model, ~22.7M parameters, 384-dim output.
- **Why chosen**: a small, fast, CPU-friendly bi-encoder that's a common first choice for a "retrieve" stage — chosen here specifically for being small, fast, and CPU-friendly.
- **How VoxIQ uses it**: Knowledge Search's first-pass ("retrieve") stage — every FOMC-minutes chunk and meeting transcript is embedded once and stored; a query is embedded at search time and compared by cosine similarity.
- **Card**: <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2>

### 2. cross-encoder/ms-marco-MiniLM-L-6-v2 (cross-encoder reranker)
- **What it is**: a MiniLM model fine-tuned on the MS MARCO passage-ranking dataset to jointly score a (query, document) pair — not pre-computable like a bi-encoder, but measurably more accurate.
- **Why chosen**: a well-established reranker for this trade-off, used here to demonstrate the bi- vs. cross-encoder trade-off with a real "환불" (refund) vs. "날씨" (weather) example.
- **How VoxIQ uses it**: Knowledge Search's second ("rerank") stage — re-scores the bi-encoder's top candidates and shows the reordered result next to the original, so the improvement (or lack thereof) is directly visible.
- **Card**: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2>

### 3. Whisper (tiny)
- **What it is**: OpenAI's encoder-decoder speech-recognition Transformer, `tiny` checkpoint (37,184,640 parameters), trained on ~680,000 hours of multilingual audio.
- **Why chosen**: a small, CPU-friendly model + size choice for this kind of ASR task, chosen for running comfortably on CPU.
- **How VoxIQ uses it**: Meeting Transcription — turns uploaded or sample audio into text plus a detected language.
- **Card**: <https://github.com/openai/whisper> · **Paper**: Radford, A. et al. "Robust Speech Recognition via Large-Scale Weak Supervision." 2022. <https://arxiv.org/abs/2212.04356>

### 4. Qwen/Qwen2.5-0.5B-Instruct (local code-generation agent)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: a small, capable open-weight LLM well-suited for fully offline, no-API-key text/code generation — as the project brief encourages.
- **How VoxIQ uses it**: default (no-key) provider for the Analytics Agent — turns a natural-language question into a short Python snippet.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 5. qwen/qwen3-8b via OpenRouter (optional cloud upgrade)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API.
- **Why chosen**: cheap ($0.117 / $0.455 per million input/output tokens, verified live against openrouter.ai during an earlier product's build in this series), and the project brief specifically asks for an OpenRouter-validated cloud path this round.
- **How VoxIQ uses it**: strictly opt-in (a checkbox on the Analytics Agent page) alternative to the local LLM for the same code-generation task.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

### 6. GPT-2 (tokenizer & attention explorer)
- **What it is**: OpenAI's 117M-parameter Transformer language model — used here purely as an inspection tool, not to generate anything.
- **Why chosen**: a tokenizer family commonly used to illustrate Korean vs. English token-count inefficiency (e.g. ~8 tokens for an English sentence vs. ~46 for its Korean translation with the base GPT-2 tokenizer).
- **How VoxIQ uses it**: the Tokenizer & Attention Explorer page — real BPE tokenization plus a genuine self-attention weight heatmap (averaged across heads for a chosen layer), making the "attention connects every token to every other token" concept literally visible.
- **Card**: <https://huggingface.co/gpt2> · **Paper**: Radford, A. et al. "Language Models are Unsupervised Multitask Learners." 2019.

## Key terms

| Term | Meaning in this project |
|---|---|
| **Bi-encoder vs. cross-encoder** | A bi-encoder embeds the query and each document *independently* (fast, pre-computable, good for the first "retrieve" pass over many documents); a cross-encoder feeds the query and document *together* into one model (slower — must run per pair at query time — but more accurate). Retrieve-then-rerank pipelines like Knowledge Search use a bi-encoder to narrow thousands of candidates down to a handful, then a cross-encoder to precisely order just those few. |
| **Chunking (with overlap)** | Splitting a long document into smaller, independently-searchable passages so retrieval doesn't have to match against (or return) an entire multi-thousand-word document at once; overlapping the chunk boundaries (here, 40 of 220 words) avoids losing content that straddles a cut point. A standard technique for making long documents retrievable. |
| **Teaching-grade sandbox** | A code-isolation approach (here: subprocess + OS resource limits + a restricted `__builtins__` set) that stops *accidental* misuse and resource exhaustion but is openly acknowledged — by this project — to be escapable by a determined attacker via Python introspection tricks. Distinct from a *production* security boundary (container-per-execution, microVMs, or a managed service like E2B). |
| **Self-attention** | The mechanism by which a Transformer lets every token's representation be updated based on every other token's representation, weighted by a learned relevance score — the Tokenizer Explorer's heatmap visualizes exactly these weights for one chosen layer of GPT-2. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call is recorded with who made it, which model, how long it took, and whether it succeeded, mirroring the "감사 추적" concept common in agentic-AI system design. |
