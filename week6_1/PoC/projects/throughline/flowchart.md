# Throughline — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).

## 1. Authentication (`security.py`, `routers/auth.py`)

Identical architecture to Verity's and Threshold's own — see either project's `flowchart.md` §1 for
the diagram (access+refresh rotation, CSRF double-submit, account lockout); the mechanism is shared
verbatim, only the seeded org/company data differs.

## 2. One message turn (`chains/orchestrator.py::prepare_turn` / `finalize_turn`)

```mermaid
flowchart TD
    A["POST /api/cases/{id}/messages"] --> B["redact(message) -> persist ConversationTurn(human)"]
    B --> C["extraction.extract(message) -> ExtractedFacts"]
    C --> D["apply_extracted_facts() -- conflict guardrail, see flowchart 4"]
    D --> E["router.route(message) -> RouterDecision<br/>Pydantic-validated, one bounded retry"]
    E --> F{"action?"}
    F -- reply --> G["combined_content = redacted message"]
    F -- tool --> H["_autofill_args() from MemoryFact if an arg is missing"]
    H --> I["execute the real deterministic tool function"]
    I --> J["persist ConversationTurn(tool)"]
    J --> K["combined_content = message + tool result"]
    G --> L
    K --> L["_facts_system_prompt() -- inject current MemoryFact rows<br/>see debug/issue-02: this is what makes memory FUNCTIONAL"]
    L --> M["stream_reply([facts SystemMessage] + windowed history + combined turn)"]
    M --> N["SSE token deltas -- live streaming reply"]
    N --> O["redact(reply) -> persist ConversationTurn(ai)"]
    O --> P["maybe_summarize() if the window overflowed -- see flowchart 3"]
    P --> Q["log_action() -- hash-chained audit entry"]
```

## 3. Dual-strategy memory (`chains/memory_store.py`)

```mermaid
flowchart TD
    A["windowed_messages(case_id, window_turns)"] --> B["trim_messages(history, max_tokens=window_turns*2, strategy='last')"]
    B --> C["real LCEL trim -- mirrors a common history[-6:] window technique"]
    D["maybe_summarize() after every turn"] --> E{"turns beyond summarized_through_turn_id > live window size?"}
    E -- no --> F["no-op -- nothing overflowed yet"]
    E -- yes --> G["_summary_chain.invoke() -- SUMMARY_PROMPT | local_llm | StrOutputParser()"]
    G --> H["real ChatPromptTemplate piped into the shared Runnable --<br/>see debug/issue-03: this exact composition shape crashed<br/>the first time it ran, fixed at the Runnable's input boundary"]
    H --> I["case.case_summary updated, summarized_through_turn_id advanced"]
```

## 4. The memory-write conflict guardrail (`chains/extraction.py::apply_extracted_facts`)

```mermaid
flowchart TD
    A["A new value extracted for field_name"] --> B["confidence = 'stated' if the value appears verbatim<br/>in the source turn text, else 'inferred'"]
    B --> C{"existing MemoryFact for this field?"}
    C -- no --> D["create it -- no conflict possible"]
    C -- yes, same value --> E["no-op -- restated, not a conflict"]
    C -- yes, different value --> F{"existing confidence vs. new confidence?"}
    F -- "stated vs stated" --> G["MemoryConflictLog: pending_confirmation<br/>OLD VALUE KEPT until a human resolves it"]
    F -- "stated vs inferred" --> H["MemoryConflictLog: kept_old (auto) --<br/>a lower-confidence value never overrides a stated one"]
    F -- "inferred vs anything" --> I["MemoryConflictLog: accepted_new (auto) --<br/>overwrite allowed, but still logged, never silent"]
```

## 5. Structured-output tool routing (`chains/router.py::route`)

```mermaid
flowchart TD
    A["local_llm.invoke([system, human]) -- attempt 1"] --> B{"json.loads + Pydantic validate?"}
    B -- ok --> C["RouterResult: attempts=1, fell_back=False"]
    B -- fail --> D["retry: append the malformed reply + a correction instruction"]
    D --> E["local_llm.invoke(...) -- attempt 2"]
    E --> F{"valid this time?"}
    F -- ok --> G["RouterResult: attempts=2, fell_back=False"]
    F -- fail --> H["RouterResult: action=reply, fell_back=True --<br/>never a silent guess at a tool/args, see debug/README.md<br/>for the measured first-attempt reliability this is based on"]
```

## 6. Model routing / cloud escalation (`ml/llm.py`, `routers/cases.py::escalate_case`)

```mermaid
flowchart TD
    A["POST /api/cases/{id}/escalate"] --> B["budget check: today's spend + estimate <= daily limit?"]
    B -- no --> C["402 -- budget cap reached, skipped, never silent"]
    B -- yes --> D["redact(question) + redact(case_context)<br/>the ONE point content actually leaves this container"]
    D --> E["escalate_to_cloud() -- OpenRouter qwen/qwen3-8b<br/>ZERO tool-calling, ZERO memory-write capability"]
    E --> F["log_action('case.escalate', latency_ms=real)"]
```

## 7. Purge / right-to-erasure (`chains/orchestrator.py::purge_case`)

```mermaid
flowchart TD
    A["POST /api/cases/{id}/purge"] --> B["count turns_deleted, facts_deleted BEFORE deleting"]
    B --> C["DELETE conversation_turns, memory_facts, memory_conflict_logs WHERE case_id=..."]
    C --> D["vectorstore.delete('case-{id}')"]
    D --> E["DELETE the caller_cases row itself"]
    E --> F["INSERT retention_requests --<br/>case_id + counts + actor ONLY, never the purged content"]
    F --> G["log_action('case.purge') -- one audit entry"]
```

## 8. Hash-chained audit log (`audit.py`)

Identical mechanism to Verity's and Threshold's own — see either project's `flowchart.md` for the
diagram (per-row `entry_hash = sha256(prev_hash + content)`, and the admin "Verify integrity" walk
that pinpoints the first broken row).

## 9. Container bootstrap sequence (`main.py`)

```mermaid
flowchart TD
    A["Container starts"] --> B{"ENFORCE_SECURE_DEFAULTS=true AND still default secret/password?"}
    B -- yes --> C["exit(1) -- refuse to boot insecurely"]
    B -- no --> D["Base.metadata.create_all()"]
    D --> E["_seed() -- Organization, admin User, BudgetSetting, MemorySetting (idempotent)"]
    E --> F["/api/health responds 'ok' immediately"]
    E --> G["background thread: _warm_cache()"]
    G --> H["_warm_step('embeddings')"]
    H --> I["_warm_step('local_agent')"]
    I --> J{"any step failed?"}
    J -- yes --> K["logged, retried lazily on first real request"]
    J -- no --> L["/api/health/ready -> all_warm: true"]
```
