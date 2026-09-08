# Compass — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

Identical to the Week1-13 PoCs — same JWT + bcrypt design, same shape-only email validator (not `EmailStr`, which broke `.local` admin logins in the Week1 PoC — see that project's `debug/issue-02`), reused here from the start rather than rediscovered.

```mermaid
flowchart TD
    A["POST /api/auth/signup or /login"] --> B{"email exists? (signup)\npassword matches hash? (login)"}
    B -- "no / mismatch" --> C["401/400 error"]
    B -- "ok" --> D["hash_password() / verify_password()\n(passlib + bcrypt)"]
    D --> E["create_access_token(email)\n(python-jose, HS256, 24h expiry)"]
    E --> F["Set-Cookie: access_token (httpOnly)\n+ return { user, access_token } in body"]
    F --> G["Frontend stores access_token\nin localStorage for Bearer header use"]

    H["Any protected request"] --> I["get_current_user()\ncookie OR Authorization: Bearer"]
    I --> J{"token valid & user active?"}
    J -- no --> K["401 Unauthorized"]
    J -- yes --> L["proceed to endpoint"]
    L --> M{"require_admin()?"}
    M -- "role != admin" --> N["403 Forbidden"]
    M -- "role == admin" --> O["proceed to /api/admin/*"]
```

## 2. Streaming Research (`pipeline.py`, `search/`, `ml/llm.py`, `ml/groundedness.py`, `ml/ghost_citation.py`, `routers/research.py`)

```mermaid
flowchart TD
    A["POST /api/research/sessions/{id}/entries"] --> B["web_search.search(query)"]
    B --> C{"ddgs succeeds?"}
    C -- "yes" --> D["real search results, mode=ddgs"]
    C -- "no (rate-limited/blocked)" --> E["_mock_results(), mode=mock\n(surfaced honestly to the UI)"]
    D --> F["rerank_pipeline.rerank_results()"]
    E --> F
    F --> G["embed_query + embed_passages (e5-small)\n-> bi_score, sort"]
    G --> H{"use_rerank?"}
    H -- yes --> I["reranker.rerank() -> rerank_score, re-sort"]
    H -- no --> J["top_k by bi_score"]
    I --> K["build_context_block(sources)"]
    J --> K
    K --> L["llm.stream_generate(RESEARCH_SYSTEM_PROMPT, sources+query)"]
    L --> M["SSE 'data: {delta}' per token to the browser"]
    M --> N["groundedness.verify(report, source_texts)"]
    N --> O["ghost_citation.check(report, source_urls)"]
    O --> P["fresh SessionLocal(): INSERT report_entries\n+ embed+upsert into Chroma for Archive search"]
    P --> Q["SSE 'data: {done, sources, groundedness, ghost_citations}'"]
```

## 3. Grounding Lab — self-hosted pipeline vs. OpenRouter managed search (`routers/grounding_lab.py`)

```mermaid
flowchart TD
    A["POST /api/grounding-lab/compare"] --> B["Arm 1: gather_sources() -> rerank -> local LLM\n(free, always runs)"]
    A --> C["get_daily_budget() / today_openrouter_spend()"]
    C --> D{"spent + est_cost > daily_limit?"}
    D -- "yes" --> E["Arm 2 SKIPPED\nopenrouter_error explains why\n(never silently over-spent)"]
    D -- "no" --> F["Arm 2: llm.openrouter_web_search()\nplugins:[{id:'web'}], real cost ~$0.007+"]
    F --> G["annotations[].url_citation -> real citations"]
    B --> H["ghost_citation.check() on both arms independently"]
    G --> H
    E --> I["persist both arms as report_entries\n(mode=grounding_lab, cost_usd tracked)"]
    H --> I
    I --> J["return both arms + budget status to the UI"]
```

## 4. Trend Radar — structured 3-lens extraction (`pipeline.py`, `routers/trend_radar.py`)

```mermaid
flowchart TD
    A["POST /api/trend-radar/evaluate"] --> B["gather_sources(topic) -> rerank"]
    B --> C["llm.stream_generate(RADAR_SYSTEM_PROMPT, sources)\n(collected, not streamed to the UI)"]
    C --> D["_extract_first_json_object()\nbrace-depth counting, not a greedy regex\n(see debug/issue-01)"]
    D --> E{"balanced JSON found\n& has cost/security/approval keys?"}
    E -- no --> F["extraction_failed=true\nraw model text shown honestly\n(never a fabricated verdict)"]
    E -- yes --> G["radar = {cost, security, approval}\neach: Low | Medium | High | Insufficient evidence"]
    F --> H["INSERT report_entries (mode=trend_radar)"]
    G --> H
```

## 5. Cost Governance (`models.BudgetSetting`, `routers/admin.py`, `routers/research.py`)

```mermaid
flowchart TD
    A["Admin sets daily_limit_usd via PUT /api/admin/budget"] --> B[("budget_settings, id=1 singleton")]
    C["Any OpenRouter-paid call site\n(Grounding Lab's openrouter_web_search)"] --> D["today_openrouter_spend(db)\nSUM(cost_usd) WHERE created_at >= start_of_today"]
    D --> E{"spent + this_call_cost > limit?"}
    E -- yes --> F["call skipped, error explains the cap\n(a cost-governance discipline a typical\nbaseline implementation never implements)"]
    E -- no --> G["call proceeds, real cost recorded\nas a report_entries row"]
    G --> D
    B --> E
```

## 6. Container bootstrap sequence (`main.py`)

```mermaid
flowchart TD
    A["Container starts"] --> B["Base.metadata.create_all()"]
    B --> C["_seed_admin_and_budget()\n(idempotent)"]
    C --> D["/api/health responds 'ok' immediately"]
    C --> E["background thread: _warm_cache()"]
    E --> F["_warm_step('model:embeddings')"]
    F --> G["_warm_step('model:reranker')"]
    G --> H["_warm_step('model:local_llm')"]
    H --> I["_warm_step('search:connectivity')\nweb_search.connectivity_check()\n(ddgs failure here is non-fatal —\nmock fallback, not a bootstrap error)"]
    I --> J{"any step failed?"}
    J -- yes --> K["logged, will retry lazily on first real request\n(no cascading failure — see debug/README.md\nfor the Week4 precedent this isolation prevents)"]
    J -- no --> L["bootstrap_complete.set()\n/api/health/ready -> all_warm: true"]
```
