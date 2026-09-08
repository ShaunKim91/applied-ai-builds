# Threshold — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).

## 1. Authentication (`security.py`, `routers/auth.py`)

Identical architecture to Verity's own — see that project's `flowchart.md` §1 for the diagram
(access+refresh rotation, CSRF double-submit, account lockout); the mechanism is shared verbatim,
only the seeded org/company data differs.

## 2. The ReAct + guardrail streaming loop (`agent/react_loop.py`, `agent/guardrails.py`, `agent/orchestrator.py`)

```mermaid
flowchart TD
    A["POST /api/agent/runs"] --> B["INSERT agent_runs (status=RUNNING)"]
    B --> C["run_react_loop(run_id) — fresh SessionLocal()"]
    C --> D["stream_one_step(messages)<br/>TextIteratorStreamer, few-shot prompt"]
    D --> E["SSE 'data: {delta}' per token"]
    E --> F["truncate_generation(raw)"]
    F --> G{"'Final Answer:' in output?"}
    G -- yes --> H["persist final_answer step<br/>UPDATE status=COMPLETED"]
    G -- no --> I["parse_action(gen) -> (tool_name, RAW arg, quotes untouched)"]
    I --> J["check_guardrails()<br/>step limit -> permission -> cost cap -><br/>AMOUNT-AWARE HITL (parses arg via tools.split_args)"]
    J --> K{"verdict"}
    K -- "STOPPED_* / BLOCKED_PERMISSION" --> L["persist 'blocked' step, RETURN"]
    K -- "AWAITING_APPROVAL" --> M["INSERT approval_requests, RETURN — see flowchart 3"]
    K -- "ALLOWED" --> N["execute_tool(): tool's OWN clean_arg()/split_args()<br/>strips quotes from final tokens — see debug/issue-01"]
    N --> O["persist 'observation' step, SSE step_complete"]
    O --> D
    H --> P["SSE 'data: {done, status: COMPLETED}'"]
```

## 3. The approval-resume flow (`routers/approvals.py`)

```mermaid
flowchart TD
    A["Run pauses: AWAITING_APPROVAL"] --> B["Admin reviews tool_name + tool_arg on the Approvals page"]
    B --> C{"decide: approve or deny?"}
    C -- approve --> D["execute_tool() — the REAL tool runs, for the first time"]
    C -- deny --> E["inject a denial observation instead"]
    D --> F["run_react_loop(run_id, resume_injection=...)<br/>drained synchronously, no live client attached"]
    E --> F
    F --> G["messages_json restored -> loop continues<br/>the SAME conversation to Final Answer or another stop"]
```

## 4. Amount-aware HITL (`guardrails.py::check_guardrails`, `_parse_payout_amount`)

```mermaid
flowchart TD
    A["tool_name == issue_claim_payout?"] -->|no| B["static HITL check: in hitl_tools?"]
    A -->|yes| C["_parse_payout_amount(arg)<br/>tools.split_args() — quote-aware"]
    C --> D{"amount parsed successfully?"}
    D -- no --> E["AWAITING_APPROVAL — fails SAFE,<br/>an unparsable amount always requires a human"]
    D -- yes --> F{"amount > payout_approval_threshold_usd?"}
    F -- yes --> E
    F -- no --> G["ALLOWED — executes immediately,<br/>no human needed for a small payout"]
```

## 5. Model routing / cloud escalation (`ml/llm.py`, `routers/agent.py`)

```mermaid
flowchart TD
    A["POST /api/agent/runs/{id}/escalate"] --> B{"status in (STOPPED_STEP_LIMIT, COMPLETED)?"}
    B -- no --> C["409"]
    B -- yes --> D["budget check: today's spend + estimate <= daily limit?"]
    D -- no --> E["402 — budget cap reached, skipped, never silent"]
    D -- yes --> F["escalate_to_cloud(question, trace_text)<br/>timed with time.perf_counter()"]
    F --> G["OpenRouter qwen/qwen3-8b<br/>ZERO tool-calling capability — cannot call issue_claim_payout"]
    G --> H["persist cloud_escalation step<br/>UPDATE synth_mode, cloud_cost_usd, status=COMPLETED"]
    H --> I["log_action('agent.escalate', latency_ms=real)"]
```

## 6. Hash-chained audit log (`audit.py`)

Identical mechanism to Verity's own — see that project's `flowchart.md` §5 for the diagram
(per-row `entry_hash = sha256(prev_hash + content)`, and the admin "Verify integrity" walk that
pinpoints the first broken row).

## 7. The stale-run reaper (`routers/agent.py::_reap_stale_runs`)

```mermaid
flowchart TD
    A["GET /api/agent/runs or GET /api/agent/runs/{id}"] --> B["_reap_stale_runs(db, org_id) — called first, lazily"]
    B --> C["query: status=RUNNING AND updated_at < now - 180s"]
    C --> D{"any stale rows?"}
    D -- no --> E["proceed to the real request handler"]
    D -- yes --> F["UPDATE status=FAILED, honest explanation"]
    F --> E
```

## 8. Container bootstrap sequence (`main.py`)

```mermaid
flowchart TD
    A["Container starts"] --> B{"ENFORCE_SECURE_DEFAULTS=true AND still default secret/password?"}
    B -- yes --> C["exit(1) — refuse to boot insecurely"]
    B -- no --> D["Base.metadata.create_all()"]
    D --> E["_seed() — Organization, admin User, BudgetSetting, GuardrailSetting (idempotent)"]
    E --> F["/api/health responds 'ok' immediately"]
    E --> G["background thread: _warm_cache()"]
    G --> H["_warm_step('embeddings')"]
    H --> I["_warm_step('local_agent')"]
    I --> J{"any step failed?"}
    J -- yes --> K["logged, retried lazily on first real request"]
    J -- no --> L["/api/health/ready -> all_warm: true"]
```
