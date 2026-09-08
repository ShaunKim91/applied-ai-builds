# Verity — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).

## 1. Authentication — access+refresh rotation, CSRF, lockout (`security.py`, `routers/auth.py`)

```mermaid
flowchart TD
    A["POST /api/auth/login"] --> B{"account locked?<br/>(locked_until > now)"}
    B -- yes --> C["423 Locked"]
    B -- no --> D{"password correct?"}
    D -- no --> E["record_failed_login()<br/>5th failure -> locked_until = now+15min<br/>401"]
    D -- yes --> F["record_successful_login()<br/>reset failed_login_attempts"]
    F --> G["create_access_token() (20 min JWT)<br/>issue_refresh_token() (7 day, hashed at rest)"]
    G --> H["Set-Cookie: access_token, refresh_token (httpOnly)<br/>+ csrf_token (readable)"]

    I["Any mutating request"] --> J{"X-CSRF-Token header ==<br/>csrf_token cookie?"}
    J -- no --> K["403"]
    J -- yes --> L["get_current_user() decodes access_token cookie"]
    L --> M{"valid & not expired?"}
    M -- no --> N["401 -> frontend calls /api/auth/refresh"]
    M -- yes --> O["proceed"]

    P["POST /api/auth/refresh"] --> Q["rotate_refresh_token():<br/>look up by hash, check not expired/revoked"]
    Q --> R{"valid?"}
    R -- no --> S["401 (also catches reuse of an already-rotated token)"]
    R -- yes --> T["revoke old, issue_refresh_token() new<br/>new access_token<br/>Set-Cookie both"]
```

## 2. Grounded research streaming (`pipeline.py`, `ml/llm.py`, `routers/research.py`)

```mermaid
flowchart TD
    A["POST /api/research/query"] --> B{"mode?"}
    B -- quick/precedent_brief --> C["pipeline.gather_claims_sources()<br/>jurisdictions.search() -> rerank_pipeline"]
    B -- (radar is a separate router) --> Z["see flowchart 4"]
    C --> D["build_context_block(sources)"]
    D --> E["stream_generate(GROUNDING or BRIEF prompt)"]
    E --> F["SSE 'data: {delta}' per token"]
    F --> G["groundedness.verify(report, source_texts)"]
    G --> H["ghost_citation.check(report, urls)<br/>+ check_entities(report, source_texts) — see debug/issue-03"]
    H --> I["fraud_signals.check(query+report) — keyword-only, see debug/issue-02"]
    I --> J["classify_source_trust() per source"]
    J --> K["INSERT report_entries (org-scoped)"]
    K --> L["embed + upsert into Chroma (Library search)"]
    L --> M["SSE 'data: {done, entry: {...full payload...}}'"]
```

## 3. Precedent Brief parsing (`routers/research.py::_parse_brief`)

```mermaid
flowchart TD
    A["Raw model output"] --> B["Scan lines for exact labels:<br/>'Issue:' 'Governing Authority:'<br/>'Facts Applied:' 'Recommendation:' 'Sources:'"]
    B --> C{"label found on this line?"}
    C -- yes --> D["start new section, strip label prefix"]
    C -- no --> E["append line to the CURRENT open section<br/>(handles multi-line answers)"]
    D --> F["brief dict: {issue, governing_authority,<br/>facts_applied, recommendation, sources}"]
    E --> F
```

## 4. Vendor & Tool Adoption Radar (`search/web_search.py`, `routers/radar.py`)

```mermaid
flowchart TD
    A["POST /api/radar/evaluate"] --> B["web_search.search() — REAL ddgs live search<br/>(never used for claims research, see README)"]
    B --> C{"ddgs succeeds?"}
    C -- yes --> D["real results, search_mode=ddgs"]
    C -- no --> E["_MOCK_RESULTS, search_mode=mock"]
    D --> F["rerank_pipeline.rerank_results()"]
    E --> F
    F --> G["stream_generate(RADAR_SYSTEM_PROMPT)"]
    G --> H["pipeline.extract_first_json_object()<br/>brace-depth counting, not a greedy regex"]
    H --> I{"balanced JSON with cost/security/approval_friction?"}
    I -- no --> J["extraction_failed=true, raw text shown honestly"]
    I -- yes --> K["radar = {cost, security, approval_friction}"]
    J --> L["INSERT report_entries (mode=radar)"]
    K --> L
```

## 5. Hash-chained audit log (`audit.py`)

```mermaid
flowchart TD
    A["log_action(user, action, ...)"] --> B["fetch last AuditLog row's entry_hash as prev_hash<br/>('' if this is the first row)"]
    B --> C["INSERT row, flush() to get its real created_at"]
    C --> D["entry_hash = sha256(prev_hash + canonical_json(row content))"]
    D --> E["UPDATE row SET entry_hash, commit()"]

    F["Admin clicks 'Verify integrity'"] --> G["GET /api/admin/audit-log/verify"]
    G --> H["walk ALL rows in id order"]
    H --> I["recompute expected_hash from each row's OWN content<br/>+ the PREVIOUS row's stored entry_hash"]
    I --> J{"expected == stored entry_hash?"}
    J -- yes, all rows --> K["intact: true"]
    J -- no, at row N --> L["intact: false, first_broken_id: N<br/>— any edit/delete/reorder after this row breaks HERE"]
```

## 6. Rate limiting (`rate_limit.py`)

```mermaid
flowchart TD
    A["Request to a rate-limited route"] --> B["key = scope:client_ip<br/>(scope = 'auth' or 'ai')"]
    B --> C["drop timestamps older than 60s from this key's deque"]
    C --> D{"deque length >= limit?"}
    D -- yes --> E["429 Too Many Requests"]
    D -- no --> F["append now(), proceed"]
```

## 7. Container bootstrap sequence (`main.py`)

```mermaid
flowchart TD
    A["Container starts"] --> B{"ENFORCE_SECURE_DEFAULTS=true<br/>AND still using default secret/password?"}
    B -- yes --> C["exit(1) — refuse to boot insecurely"]
    B -- no --> D["Base.metadata.create_all()"]
    D --> E["_seed() — Organization, admin User, BudgetSetting (idempotent)"]
    E --> F["/api/health responds 'ok' immediately"]
    E --> G["background thread: _warm_cache()"]
    G --> H["_warm_step('embeddings')"]
    H --> I["_warm_step('reranker')"]
    I --> J["_warm_step('local_llm')"]
    J --> K["_warm_step('search:connectivity') — ddgs check, Radar-only, non-fatal on failure"]
    K --> L{"any step failed?"}
    L -- yes --> M["logged, retried lazily on first real request"]
    L -- no --> N["/api/health/ready -> all_warm: true"]
```
