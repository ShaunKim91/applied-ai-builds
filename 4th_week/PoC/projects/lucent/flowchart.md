# Lucent — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

Identical to the Week1-3 PoCs — same JWT + bcrypt design, same shape-only email validator (not `EmailStr`, which broke `.local` admin logins in the Week1 PoC — see that project's `debug/issue-02`), reused here from the start rather than rediscovered.

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

## 2. Streaming RAG Chat (`rag.py`, `ml/llm.py`, `ml/groundedness.py`, `routers/chat.py`)

```mermaid
flowchart TD
    A["User sends a message"] --> B["POST /api/chat/sessions/{id}/messages"]
    B --> C["INSERT chat_messages (role=user)"]
    C --> D["rag.retrieve(query, use_rerank)\nembed_query() -> vectorstore.query()\n-> optional reranker.rerank()"]
    D --> E["rag.build_context_block(sources)\nnumbered [1] [2] ... context for the prompt"]
    E --> F["llm.stream_generate(system, sources+question, provider)"]
    F --> G{"provider"}
    G -- "local (default)" --> H["TextIteratorStreamer + background thread\nyields text fragments as they generate"]
    G -- "openrouter (opt-in)" --> I["httpx.stream() SSE parsing\nyields choices[0].delta.content per event"]
    H & I --> J["each fragment -> SSE 'data: {delta}'\nstreamed to the browser in real time"]
    J --> K["full answer assembled server-side"]
    K --> L["groundedness.verify(answer, source_texts)\ncitation-index check + per-sentence similarity check"]
    L --> M["INSERT chat_messages (role=assistant,\ncitations_json, groundedness fields)"]
    M --> N["final SSE 'data: {done, citations, groundedness}'"]
    N --> O["Frontend: citation markers become clickable,\ngroundedness badge rendered"]

    style H fill:#efeaff,stroke:#6d5ce7,color:#1a1533
    style I fill:#eafcff,stroke:#22d3ee,color:#1a1533
```

## 3. Retrieval Lab — bi vs. bi+cross comparison (`rag.py`, `routers/retrieval.py`)

```mermaid
flowchart TD
    A["query text"] --> B["POST /api/retrieval/compare"]
    B --> C["rag.retrieve(query, use_rerank=False)\n-> bi_results (pure ANN cosine order)"]
    B --> D["rag.retrieve(query, use_rerank=True)\n-> cross_results (reranked order)"]
    C & D --> E["top1_changed = bi[0].id != cross[0].id"]
    E --> F["200 OK -> both rankings + top1_changed flag"]
    F --> G["Frontend renders two ranked lists side by side"]
```

## 4. Document indexing — seed corpus + uploads (`etl/seed_corpus.py`, `etl/chunking.py`, `routers/documents.py`)

```mermaid
flowchart TD
    A["Bootstrap (once) OR user upload"] --> B{"source"}
    B -- "seed (English)" --> C["seed_corpus.parse_federalist_essays()\nsplits on 'No. <roman-numeral>.' headings\n-> 85 real essays"]
    B -- "seed (Korean)" --> D["seed_corpus.fetch_korean_wikipedia_article()\nWikipedia REST API plaintext extract"]
    B -- "upload" --> E["pypdf (PDF) or raw decode (txt/md)"]
    C & D & E --> F["chunking.chunk_text()\n500 words / 50-word overlap"]
    F --> G["embeddings.embed_passages(chunks)\n'passage: ' prefix, multilingual-e5-small"]
    G --> H["INSERT documents (SQL, one row per essay/article/upload)"]
    G --> I["vectorstore.upsert() per chunk\n(document_id, chunk_index, title, language metadata)"]
```

## 5. Admin Console + Analytics (`routers/admin.py`)

```mermaid
flowchart TD
    A["Admin logs in (role=admin)"] --> B["GET /api/admin/system"]
    B --> C["COUNT(*) per table"]
    B --> D["model *._model is not None ?\n-> live loaded-status per AI model"]
    C & D --> E["system status JSON"]

    F["GET /api/admin/analytics"] --> G["query all assistant chat_messages"]
    G --> H["latencies_ms (last 30) for the bar chart"]
    G --> I["groundedness_pass_rate = passed / total"]
    G --> J["retrieval_mode_counts, documents_by_language"]
    H & I & J --> K["real, computed usage stats\n(no fabricated demo data)"]
    K --> L["Frontend: hand-rolled SVG BarChart\n+ stat cards"]
```

## 6. Container bootstrap sequence (`main.py`)

```mermaid
sequenceDiagram
    autonumber
    participant D as Docker (docker compose up)
    participant U as Uvicorn / FastAPI
    participant BG as background thread
    participant HF as HuggingFace Hub
    participant GB as gutenberg.org (Federalist Papers)
    participant WP as ko.wikipedia.org (REST API)

    D->>U: start container, run CMD
    U->>U: Base.metadata.create_all() (SQLite tables)
    U->>U: _seed_admin() (idempotent)
    U->>BG: spawn _warm_cache() thread
    U-->>D: /api/health responds 200 immediately

    Note over BG: each step below runs in its own\ntry/except (_warm_step) — an unrelated\nstep's failure never blocks the others.
    BG->>HF: load multilingual-e5-small [isolated step]
    HF-->>BG: embedding model weights
    BG->>GB: index_seed_corpus() -> parse 85 Federalist essays [isolated step]
    GB-->>BG: The Federalist Papers, full text
    BG->>WP: fetch Korean Wikipedia article
    WP-->>BG: plaintext extract
    BG->>HF: load reranker + local LLM (2 more isolated steps)
    HF-->>BG: model weights (cached to named volume)
    BG->>U: log per-step result; "all warm" only if every step succeeded

    Note over D,U: GET /api/health/ready reports real per-model +\nper-step status; a failed corpus-indexing step self-heals\nthe next time ./scripts/download_data.sh runs.
```
