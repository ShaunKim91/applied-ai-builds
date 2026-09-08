# Glossary & Model Cards — Threshold

## AI models used

### 1. intfloat/multilingual-e5-small (embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim) requiring a task-specific
  prefix (`"query: "` / `"passage: "`).
- **Why chosen**: the same embedding model validated and reused across nearly every prior PoC in
  this project series, including Verity.
- **How Threshold uses it**: embedding every finished agent run (question + final answer) for
  History's semantic search — the only retrieval role this round, since there is no live search or
  fixed corpus to index.
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. Qwen/Qwen2.5-0.5B-Instruct (the ReAct agent's own brain)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM.
- **Why chosen**: a small, openly-licensed instruct model well suited to running as a local
  ReAct agent's "brain" with reliable tool-calling behavior.
- **How Threshold uses it**: runs the entire Thought→Action→Observation loop locally, greedy-decoded,
  with a few-shot prompt, streamed token by token.
- **A real, measured limitation found this build**: the few-shot example only demonstrates a bare
  numeric tool argument, so for string/multi-part arguments the model improvised its own quoting
  conventions (both a whole-argument quote and separately-quoted comma-separated parts) —
  reasonable behavior for an LLM following ordinary function-call syntax, but one this project's own
  parsing needed to handle robustly rather than assume away. See `debug/issue-01`.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 3. qwen/qwen3-8b via OpenRouter (opt-in cloud escalation)
- **What it is**: an 8B-parameter Qwen3 model via OpenRouter's hosted API.
- **Why chosen**: the same model/pricing already validated in prior PoCs, including Verity.
- **How Threshold uses it**: one best-effort final-answer synthesis over the full ReAct trace when
  the local agent stalls or a user wants a second opinion — never a second independent tool-calling
  loop, and with zero tool-calling capability of its own (a real security invariant, not just an
  implementation detail: it cannot itself call `issue_claim_payout`).
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

## Key terms

| Term | Meaning in this project |
|---|---|
| **ReAct (Reason + Act)** | The Thought→Action→Observation loop this project centers on — implemented as a hand-rolled parser, not a framework, deliberately leaving room for a future round's planned LangChain framework-ization to have real contrast to build against. |
| **Guardrail check order** | Step limit → permission → cost cap → HITL, in that exact order. A common bug in naive implementations of this pattern checks these in the wrong order (cost cap before permission); Threshold implements the correct order from the start and makes the reasoning visible in the Admin UI, not just implemented silently. |
| **Amount-aware HITL** | This build's own engineering upgrade over the predecessor Cradle PoC's flat per-tool-name approval gate: `issue_claim_payout` only pauses for human approval when the requested amount exceeds an admin-configurable threshold — a small payout auto-approves, a large one doesn't. |
| **Human-in-the-Loop (HITL)** | A guardrail that pauses agent execution for a real human decision before a risky action proceeds. A typical first-pass build scaffolds this as a feature but never wires it into the shipped app; Threshold makes it real, persisted, and actionable. |
| **Model routing** | Escalating from a small, fast, free local model to a larger, paid cloud model only when needed — a common introductory technique for combining local and cloud models, implemented here as a real, opt-in, budget-gated feature with a hard security invariant: the escalation path can never itself execute a tool. |
| **Resumable run** | An `AgentRun` whose full conversation state is snapshotted to the database at every step, so execution can pause (for HITL) and later resume — potentially long after the original HTTP request ended. |
| **Stale-run reaping** | A lazy cleanup pass marking any agent run stuck `RUNNING` with no progress in 180 seconds as `FAILED` with an honest explanation — protects against a run whose stream was abandoned mid-flight staying permanently unresolvable. |
| **Hash-chained audit log** | Each `AuditLog` row stores a SHA-256 hash of its own content plus the previous row's hash — an admin can verify the whole chain and pinpoint the exact row where any tampering occurred. Shared mechanism with Verity. |
| **Fenwick Ledger** | The shared design system between Threshold and Verity — one connected company's product suite rather than two independently-styled weekly builds. Threshold uses copper as its own primary accent within the shared palette. |
