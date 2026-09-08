# Glossary & Model Cards — Cradle

## AI models used

### 1. intfloat/multilingual-e5-small (bi-encoder embeddings)
- **What it is**: a multilingual sentence-embedding model (384-dim output) covering 100+ languages
  in one shared embedding space, requiring a task-specific text prefix (`"query: "` / `"passage: "`)
  per its model card.
- **Why chosen**: the same embedding model validated and reused across the Week2/4/14_1 PoCs.
- **How Cradle uses it**: embeds every completed agent run's question+answer for History's semantic
  search — the only retrieval role this week, since there is no live search or fixed corpus to
  index.
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>

### 2. Qwen/Qwen2.5-0.5B-Instruct (the ReAct agent's own brain)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: a well-suited small instruction-tuned model for a local ReAct agent's own
  reasoning brain — also the same small local LLM validated across the Week1-5_1 PoCs.
- **How Cradle uses it**: runs the entire Thought→Action→Observation loop locally, greedy-decoded
  (`do_sample=False`) with a few-shot prompt (found necessary in practice — instructions alone
  cause format violations), streamed token by token to the browser.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 3. qwen/qwen3-8b via OpenRouter (opt-in cloud escalation)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API.
- **Why chosen**: the same model and pricing already verified live during this project series' Week1
  build, reused here for a well-documented "model routing" trend — escalating to a bigger model only
  when the local one stalls or a user wants a second opinion, rather than running it by default.
- **How Cradle uses it**: one best-effort final-answer synthesis call over the full ReAct trace —
  never a second independent tool-calling loop — strictly opt-in and gated by the same
  daily-budget-cap pattern Week5_1 Compass validated.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

### Scaffolded, not validated this round
- **OpenAI, Anthropic, direct Gemini API** — config fields exist (`config.py`'s `*_api_key_file`
  settings), not implemented or called this round.

## Key terms

| Term | Meaning in this project |
|---|---|
| **ReAct (Reason + Act)** | The Thought → Action → Observation loop this build centers on: the model reasons about what to do next, names a tool call, receives the tool's real result as an "Observation," and repeats until it can give a Final Answer. Implemented in `agent/react_loop.py` as a hand-rolled parser over the local model's own text output, not a framework — see `architecture.md` §8 for why (and why that choice deliberately leaves room for Week6_1's LangChain upgrade). |
| **Guardrail check order** | The four safety checks a tool call passes through, in order: step limit → permission (is the tool allowlisted?) → cost cap → Human-in-the-Loop. A naive implementation might check the cost cap before permission — a reproducible bug that mislabels unauthorized-tool attempts in the audit trail. Cradle implements the corrected order from the start; see `debug/issue-01`. |
| **HITL (Human-in-the-Loop)** | A guardrail that pauses agent execution for a real human decision before a risky tool call is allowed to run. A typical baseline implementation builds this as a class feature (`approval_required_tools`) but never actually populates it in its shipped app. Cradle makes it real: a pending `ApprovalRequest` row, an Approvals page, and a resume path that continues the exact same paused conversation once decided. |
| **Model routing** | Sending different requests to different-sized models based on need — a small, fast, free local model by default, escalating to a larger, paid cloud model only when the smaller one struggles. A well-documented "2025-2026 trend," rarely implemented in a typical baseline build; Cradle implements it as a real, opt-in, budget-gated feature. |
| **Resumable run** | An `AgentRun` whose full conversation state (`messages_json`) is snapshotted to the database at every step, so execution can pause (for HITL) and later resume — potentially long after the original HTTP request ended — driven by the same `run_react_loop()` generator whether streamed live or drained synchronously on resume. |
| **Stale-run reaping** | A lazy cleanup pass (`_reap_stale_runs()`) that marks any agent run stuck `RUNNING` with no progress in 180 seconds as `FAILED` with an honest explanation — protecting against a run whose SSE stream was abandoned mid-flight (a closed tab, a navigated-away browser) staying permanently unresolvable. See `debug/issue-03`. |
| **Few-shot prompting** | Including 1-2 complete worked examples of the desired Thought/Action/Observation format directly in the prompt, rather than only describing the format in instructions — a common introductory technique found necessary for a small local model to reliably follow a structured output format, and `react_loop.py::fewshot_messages()` implements it. |
| **Claymorphism** | A soft-UI visual style using a two-directional shadow recipe (a light-side highlight plus a hue-tinted soft shadow) to make flat surfaces read as puffy/extruded rather than flat-with-a-drop-shadow — this week's chosen vehicle for the "high-lightness, low-saturation pastel, genuine 3D depth" design brief. See `architecture.md` §3. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call and tool-execution decision is recorded with who, what, how long, and success/failure, mirroring the pattern reused from the Week1-5_1 PoCs. This week's own build found and fixed a real gap in it: the `latency_ms` column was hardcoded to `0.0` everywhere, never actually measuring real call duration. See `debug/issue-06`. |
