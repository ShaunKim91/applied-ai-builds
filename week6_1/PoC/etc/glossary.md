# Glossary & Model Cards — Throughline

## AI models used

### 1. intfloat/multilingual-e5-small (embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim) requiring a task-specific
  prefix (`"query: "` / `"passage: "`).
- **Why chosen**: the same embedding model validated and reused across nearly every prior PoC in
  this project series, including Verity and Threshold.
- **How Throughline uses it**: embedding each case's rolling summary for the Cases directory's
  semantic search — "has this caller called before about something similar."
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. Qwen/Qwen2.5-0.5B-Instruct (the shared local Runnable)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM.
- **Why chosen**: a small, instruction-tuned open-weight model well-suited to running locally as this
  app's shared Runnable, with specific tuned generation settings (`do_sample=False`,
  `repetition_penalty=1.15`) verified directly against the real model's behavior.
- **How Throughline uses it**: ONE shared LangChain `Runnable` (`chains/llm_runnable.py::local_llm`)
  behind chat replies, structured-output tool routing, structured memory extraction, and rolling
  summarization — each chain supplies its own leading `SystemMessage`, letting one wrapper serve four
  different LCEL chains rather than four near-duplicate generation functions.
- **A real, measured limitation found this build**: an explicit instruction not to address the
  policyholder directly (this product helps the REPRESENTATIVE, not the caller) is followed
  inconsistently — the model occasionally slips into addressing the caller by name anyway. The
  facts it relays stayed correct across every multi-turn test run; only the phrasing/addressee
  framing is imperfect, consistent with a well-known "small local models show context
  confusion" caveat.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 3. qwen/qwen3-8b via OpenRouter (opt-in cloud escalation)
- **What it is**: an 8B-parameter Qwen3 model via OpenRouter's hosted API.
- **Why chosen**: the same model/pricing already validated in Verity and Threshold.
- **How Throughline uses it**: one best-effort synthesis over a case's redacted summary and recent
  turns when a rep wants a second opinion — never a second independent tool-calling or memory-writing
  path, and with zero tool-calling capability of its own.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

## Key terms

| Term | Meaning in this project |
|---|---|
| **LCEL (LangChain Expression Language)** | The `Runnable \| Runnable` pipe-composition syntax. Used for real throughout `chains/` — routing, extraction, and summarization each compose a `ChatPromptTemplate \| Runnable \| StrOutputParser()` chain, verified against the actual installed `langchain-core==0.3.86` before being relied on. |
| **Structured-output tool routing** | Replacing a typical brittle regex `_route()` with a Pydantic-schema-validated LLM decision (tool vs. reply, which tool, what arguments) — with a measured first-try reliability, one bounded retry, and an honest fallback to a direct reply rather than a silent guess. |
| **Dual-strategy memory** | The verbatim sliding window (`trim_messages`, mirroring a common `history[-6:]` technique) plus a rolling LCEL summary for everything older — closing a well-known "memory not persisted" gap common to a typical baseline implementation, with a mechanism that also doesn't grow unbounded. |
| **Structured memory extraction** | A dedicated LCEL chain that reads one turn and extracts only what it explicitly states (caller name, policy number, a stated preference, the turn's topic) as validated JSON — the "index card" a rep sees live in the Workspace sidebar. |
| **Grounding check (extraction)** | An extracted value is only trusted as `confidence="stated"` if it actually appears in the turn it was extracted from — otherwise it's `"inferred"` and can never silently override a `"stated"` fact. The same "does this claim actually appear in the source" discipline as Verity's own `ghost_citation.py`, applied to memory instead of citations. |
| **Memory-write conflict guardrail** | Throughline's own guardrail axis (this product has no payout-capable tools, so no HITL gate is native to it): a conflicting `stated` fact is never silently overwritten — it's flagged for a human to confirm, and every overwrite decision (auto or pending) is logged. |
| **Memory-conditioned tool auto-fill** | A tool argument the representative didn't (re-)supply can be filled from a case's persisted `MemoryFact` automatically — e.g. a stated callback-time preference. The one structural capability neither Verity nor Threshold has, since neither has a notion of the same external counterparty recurring across sessions. |
| **Redaction boundary** | Pattern-based PII redaction (SSN/phone/card/email-shaped patterns) applied at persistence, at the OpenRouter escalation call, and in the live UI sidebar — one function, three call sites, explicitly not a certified PII-detection engine. |
| **Purge / right-to-erasure** | A real hard-delete cascade of a case's turns/facts/conflict logs, recording exactly one audit entry (case id, actor, timestamp — never the purged content). Cannot retract anything already sent to the OpenRouter escalation path. |
| **Hash-chained audit log** | Each `AuditLog` row stores a SHA-256 hash of its own content plus the previous row's hash — an admin can verify the whole chain and pinpoint the exact row where any tampering occurred. Shared mechanism with Verity and Threshold. |
| **Fenwick Ledger** | The shared design system across Verity, Threshold, and Throughline — one connected company's product suite rather than three independently-styled weekly builds. Throughline uses a "ledger ink" indigo as its own primary accent within the shared palette. |
