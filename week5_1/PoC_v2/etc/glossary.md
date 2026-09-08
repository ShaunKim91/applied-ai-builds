# Glossary & Model Cards — Verity

## AI models used

### 1. intfloat/multilingual-e5-small (bi-encoder embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim) requiring a task-specific
  prefix (`"query: "` / `"passage: "`).
- **Why chosen**: the same embedding model validated and reused across nearly every prior PoC in
  this project series.
- **How Verity uses it**: reranking the fictional jurisdiction corpus and real Radar web results;
  embedding every finished report for the Library's semantic search.
- **A real, measured limitation found this build**: this model's cosine similarity tracks topical/
  domain adjacency more than specific factual match for short, domain-narrow text — measured
  directly at 0.74–0.89 similarity across both genuinely relevant AND completely unrelated
  insurance-claims sentences, with no clean separating threshold. This caused two real bugs
  (`debug/issue-02`, `debug/issue-03`) and shaped this build's design (fraud-signal matching is
  keyword-only; groundedness checking is supplemented with a deterministic entity cross-check).
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. cross-encoder/ms-marco-MiniLM-L-6-v2 (cross-encoder reranker)
- **What it is**: a MiniLM model fine-tuned for joint (query, document) relevance scoring.
- **Why chosen**: reused verbatim from prior PoCs, and independently the same reranker a typical
  first-pass implementation of a search-plus-rerank pipeline tends to reach for.
- **How Verity uses it**: reordering both the fictional jurisdiction corpus results and the real
  Radar web-search results before they reach the LLM.
- **Card**: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2>

### 3. Qwen/Qwen2.5-0.5B-Instruct (local generation)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM.
- **Why chosen**: the exact small local LLM validated and reused across this project series' PoCs.
- **How Verity uses it**: streamed Quick Answer / Precedent Brief synthesis and Radar's structured
  JSON extraction — all with a strict "use ONLY the given sources" grounding instruction.
- **A real, measured limitation found this build**: despite that instruction, this model
  hallucinated "The Federal Insurance Office (FIO)" — a real US federal body — into a precedent
  brief grounded entirely in fictional sources that never mention it (`debug/issue-03`). A known
  instruction-following limitation of very small local models, not unique to this project, but
  concretely demonstrated and honestly documented here rather than assumed away.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 4. qwen/qwen3-8b via OpenRouter (opt-in cloud escalation)
- **What it is**: an 8B-parameter Qwen3 model via OpenRouter's hosted API.
- **Why chosen**: the same model/pricing already validated in prior PoCs.
- **How Verity uses it**: an opt-in "use a bigger model" toggle on the Research page, strictly
  budget-gated by the org's daily OpenRouter spend cap.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

## Key terms

| Term | Meaning in this project |
|---|---|
| **Grounding** | Answering strictly from retrieved sources rather than the model's own training-data "knowledge," with a "no guessing, cite your sources" prompt discipline. |
| **Ghost citation** | A URL the model cites that was never actually among the retrieved sources — a sign of a fabricated or paraphrased source. |
| **Entity-hallucination check** | This build's own new safety net (`check_entities()`): flags a multi-word Title Case phrase (a proper noun) named in an answer that doesn't appear verbatim in the real retrieved source text — added specifically because groundedness's own sentence-similarity check missed exactly this failure mode (`debug/issue-03`). |
| **Source trust tier** | Primary regulatory (statute/case-law/DOI-bulletin domains) / Secondary (catastrophe-event reports) / Unverified (real live web results, Radar only) — a compliance-relevant classification beyond a binary "cited or not." |
| **Fraud-pattern signal** | A keyword match against a fixed, fictional taxonomy of fraud indicators — always framed as "possible signal, not a determination, route to SIU." Deliberately keyword-only after a measured embedding-similarity false-positive problem (`debug/issue-02`). |
| **Hash-chained audit log** | Each `AuditLog` row stores a SHA-256 hash of its own content plus the previous row's hash — an admin action can verify the whole chain and pinpoint the exact row where any tampering occurred. |
| **CSRF double-submit** | A readable `csrf_token` cookie whose value the SPA must echo back as an `X-CSRF-Token` header on every mutating request — a third-party site can ride a user's cookies but can't read them to construct a matching header. |
| **Refresh token rotation** | A refresh token is single-use: presenting it issues a new one and revokes the old — reusing an already-rotated token is rejected, a signal of possible theft. |
| **Fictional jurisdiction corpus** | Verity's claims-research knowledge base — six invented jurisdictions with invented statutes/case law/DOI bulletins, used instead of live web search specifically to avoid any risk of echoing real regulatory text as if verified. |
