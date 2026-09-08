# Cradle — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

Identical to the Week1-5_1 PoCs — same JWT + bcrypt design, same shape-only email validator, reused
here from the start rather than rediscovered.

```mermaid
flowchart TD
    A["POST /api/auth/signup or /login"] --> B{"email exists? (signup)\npassword matches hash? (login)"}
    B -- "no / mismatch" --> C["401/400 error"]
    B -- "ok" --> D["hash_password() / verify_password()\n(passlib + bcrypt)"]
    D --> E["create_access_token(email)\n(python-jose, HS256, 24h expiry)"]
    E --> F["return { user, access_token }"]
    F --> G["Frontend stores access_token\nin localStorage for Bearer header use"]

    H["Any protected request"] --> I["get_current_user()\ncookie OR Authorization: Bearer"]
    I --> J{"token valid & user active?"}
    J -- no --> K["401 Unauthorized"]
    J -- yes --> L["proceed to endpoint"]
    L --> M{"require_admin()?"}
    M -- "role != admin" --> N["403 Forbidden"]
    M -- "role == admin" --> O["proceed to /api/admin/*"]
```

## 2. The ReAct + guardrail streaming loop (`agent/react_loop.py`, `agent/guardrails.py`, `agent/orchestrator.py`, `routers/agent.py`)

```mermaid
flowchart TD
    A["POST /api/agent/runs"] --> B["INSERT agent_runs (status=RUNNING)"]
    B --> C["run_react_loop(run_id) — fresh SessionLocal()"]
    C --> D["stream_one_step(messages)\nTextIteratorStreamer, few-shot prompt"]
    D --> E["SSE 'data: {delta}' per token to the browser"]
    E --> F["truncate_generation(raw)\nstop before the model hallucinates\nits own fake Observation: line"]
    F --> G{"'Final Answer:' in output?"}
    G -- yes --> H["persist final_answer step\nUPDATE agent_runs SET status=COMPLETED"]
    G -- no --> I["parse_action(gen) -> (tool_name, arg)"]
    I --> J["check_guardrails()\nSTEP LIMIT -> PERMISSION -> COST CAP -> HITL\n(corrected order, see debug/issue-01)"]
    J --> K{"verdict"}
    K -- "STOPPED_STEP_LIMIT /\nBLOCKED_PERMISSION /\nSTOPPED_COST_CAP" --> L["persist 'blocked' step\nUPDATE status, done=true, RETURN"]
    K -- "AWAITING_APPROVAL\n(issue_refund is HITL-gated)" --> M["INSERT approval_requests (pending)\nUPDATE status=AWAITING_APPROVAL\ndone=true, RETURN — see flowchart 3"]
    K -- "ALLOWED" --> N["execute_tool(tool_name, arg)\n— the REAL tool runs"]
    N --> O["persist 'observation' step\nUPDATE spent_cost\nSSE 'data: {step_complete, step_count}'"]
    O --> D
    H --> P["SSE 'data: {done, status: COMPLETED}'"]
```

## 3. The approval-resume flow (`routers/approvals.py`, `agent/orchestrator.py`)

The one guardrail a typical baseline implementation builds as a class feature but never actually
wires into a shipped app — see `debug/issue-01`'s companion finding and `architecture.md` §2.

```mermaid
flowchart TD
    A["Run pauses: AWAITING_APPROVAL\n(from flowchart 2, step K)"] --> B["Approvals page polls\nGET /api/approvals?status=pending"]
    B --> C["Admin reviews tool_name + tool_arg\n(e.g. issue_refund(DEMO-42))"]
    C --> D{"POST /api/approvals/{id}/decide\n{approve: true|false}"}
    D -- "approve=true" --> E["execute_tool() — the REAL tool\nruns now, for the first time"]
    E --> F["resume_injection = {kind: 'resumed',\nobservation_message: real tool result}"]
    D -- "approve=false" --> G["resume_injection = {kind: 'resumed',\nobservation_message: 'denied: <reason>'}"]
    F --> H["run_react_loop(run.id, resume_injection=...)\ndrained SYNCHRONOUSLY (no live client attached)"]
    G --> H
    H --> I["messages_json restored from the DB\n-> loop continues the SAME conversation"]
    I --> J["agent reacts to the real result or the denial\n-> eventually reaches Final Answer or another guardrail stop"]
    J --> K["UPDATE approval_requests SET status, resolved_by_id\nreturn {approval, run_result} to the admin"]
```

## 4. Model routing / cloud escalation (`ml/llm.py`, `routers/agent.py`)

```mermaid
flowchart TD
    A["POST /api/agent/runs/{id}/escalate"] --> B{"run.status in\n(STOPPED_STEP_LIMIT, COMPLETED)?"}
    B -- no --> C["409 — escalation not offered\nfor this run's current status"]
    B -- yes --> D["get_daily_budget() / today_openrouter_spend()"]
    D --> E{"spent + estimated_cost > daily_limit?"}
    E -- yes --> F["402 — budget cap reached,\nescalation skipped, never silent"]
    E -- no --> G["escalate_to_cloud(question, trace_text)\ntimed with time.perf_counter() — see debug/issue-06"]
    G --> H["OpenRouter qwen/qwen3-8b\none best-effort final answer —\nNOT a second tool-calling loop"]
    H --> I["persist cloud_escalation step\nUPDATE synth_mode=openrouter, cloud_cost_usd\nUPDATE status=COMPLETED if not already"]
    I --> J["log_action('agent.escalate', latency_ms=real)"]
```

## 5. Cost governance (`models.BudgetSetting`, `routers/admin.py`, `routers/agent.py`)

Reused verbatim from Week5_1 Compass's own daily-budget-cap pattern, applied here to the escalation
call instead of a paid search call.

```mermaid
flowchart TD
    A["Admin sets daily_limit_usd via PUT /api/admin/budget"] --> B[("budget_settings, id=1 singleton")]
    C["Any escalation attempt"] --> D["today_openrouter_spend(db)\nSUM(cloud_cost_usd) WHERE created_at >= start_of_today"]
    D --> E{"spent + this_call_cost > limit?"}
    E -- yes --> F["call skipped, 402 explains the cap"]
    E -- no --> G["call proceeds, real cost recorded\non the agent_runs row"]
    G --> D
    B --> E
```

## 6. Container bootstrap sequence (`main.py`)

One step shorter than Week5_1 Compass's — no web-search connectivity check this week, since
Cradle's tools are all local Python functions with no live external dependency.

```mermaid
flowchart TD
    A["Container starts"] --> B["Base.metadata.create_all()"]
    B --> C["_seed_admin_and_guardrails_and_budget()\n(idempotent)"]
    C --> D["/api/health responds 'ok' immediately"]
    C --> E["background thread: _warm_cache()"]
    E --> F["_warm_step('model:embeddings')\nintfloat/multilingual-e5-small"]
    F --> G["_warm_step('model:local_agent')\nQwen/Qwen2.5-0.5B-Instruct"]
    G --> H{"any step failed?"}
    H -- yes --> I["logged, will retry lazily on first real request\n(no cascading failure — see debug/README.md)"]
    H -- no --> J["bootstrap_complete.set()\n/api/health/ready -> all_warm: true"]
```

## 7. The stale-run reaper (`routers/agent.py::_reap_stale_runs`)

New this week — see `debug/issue-03` for the full incident that motivated it.

```mermaid
flowchart TD
    A["GET /api/agent/runs\nor GET /api/agent/runs/{id}"] --> B["_reap_stale_runs(db, owner_id)\ncalled first, lazily"]
    B --> C["query: status=RUNNING\nAND updated_at < now - 180s"]
    C --> D{"any stale rows?"}
    D -- no --> E["proceed to the real request handler,\nnothing to do"]
    D -- yes --> F["UPDATE status=FAILED\nfinal_answer = honest explanation\n('this run was abandoned...')"]
    F --> E
```
