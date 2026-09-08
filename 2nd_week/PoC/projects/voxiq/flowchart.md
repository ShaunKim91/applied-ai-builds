# VoxIQ — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

Identical to the Week1 PoC ("CommerceIQ") — same JWT + bcrypt design, same shape-only email validator (not `EmailStr`, which broke `.local` admin logins there — see that project's `debug/issue-02`), reused here from the start rather than rediscovered.

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

## 2. Meeting Transcription (`ml/whisper_asr.py`, `routers/meetings.py`)

```mermaid
flowchart TD
    A["Upload audio OR pick a sample\n(jfk.flac + 5 LibriSpeech clips)"] --> B["POST /api/meetings/transcribe\nor /transcribe-sample/{filename}"]
    B --> C["whisper_asr._load()\nlazy-load Whisper 'tiny' (37.2M params),\nffmpeg decodes the audio container"]
    C --> D["model.transcribe(audio_path, fp16=False)\n-> {text, language}"]
    D --> E["INSERT meetings (SQLite)\ntranscript + detected_language + latency"]
    E --> F["embeddings.embed(transcript)\n(all-MiniLM-L6-v2)"]
    F --> G["vectorstore.upsert('meeting-{id}', transcript, vector,\n{source: meeting, meeting_id, filename})"]
    G --> H["INSERT audit_logs (model, latency_ms)"]
    H --> I["200 OK -> {transcript, language, latency_ms}"]
```

## 3. Knowledge Search — bi-encoder vs. cross-encoder (`ml/embeddings.py`, `ml/reranker.py`, `routers/search.py`)

```mermaid
flowchart TD
    A["query text, top_k"] --> B["POST /api/search"]
    B --> C["embeddings.embed(query)\n(all-MiniLM-L6-v2, normalized)"]
    C --> D["vectorstore.query(vector, top_k*3)\nover-fetch candidates from Chroma\n(FOMC minutes chunks + meeting transcripts)"]
    D --> E["bi_encoder_results = candidates[:top_k]\n(pure ANN cosine order — the 'retrieve' stage)"]
    D --> F{"candidates empty?"}
    F -- no --> G["reranker.rerank(query, [c.text for c in candidates])\n(ms-marco-MiniLM-L-6-v2, joint query+doc encoding)"]
    G --> H["re-sort candidates by cross-encoder score\n-> cross_encoder_results[:top_k]\n(the 'rerank' stage)"]
    F -- yes --> H
    E & H --> I["top1_changed = bi[0].id != cross[0].id"]
    I --> J["INSERT search_queries + audit_logs"]
    J --> K["200 OK -> both rankings + top1_changed flag"]
```

## 4. Analytics Agent — LLM-generated code in a sandbox (`ml/llm.py`, `ml/sandbox.py`, `routers/sandbox.py`)

```mermaid
flowchart TD
    A["natural-language request\n(use_openrouter?)"] --> B["POST /api/sandbox/analyze"]
    B --> C["_meeting_dataset(db)\n-> list of {filename, transcript, language, word_count}"]
    C --> D["llm.generate(SYSTEM_PROMPT, request, provider)"]
    D --> E{"provider"}
    E -- "local (default)" --> F["Qwen2.5-0.5B-Instruct\napply_chat_template -> model.generate()"]
    E -- "openrouter (opt-in)" --> G["read api_keys/openrouter.md\n-> httpx POST openrouter.ai/api/v1/chat/completions\n(qwen/qwen3-8b)"]
    F & G --> H["_strip_code_fences(generated text)"]
    H --> I["sandbox.run_code(code, data)"]
    I --> I1["write code + data.json to a temp dir"]
    I1 --> I2["subprocess.run([python, runner.py], timeout=10s)\nrunner.py: resource.setrlimit(RLIMIT_AS, RLIMIT_CPU)\n+ restricted __builtins__ + exec(code, sandbox_globals)"]
    I2 --> J["{stdout, stderr, exit_code, timed_out}"]
    J --> K["UPDATE sandbox_runs + INSERT audit_logs"]
    K --> L["200 OK -> generated_code + stdout + stderr"]

    style I2 fill:#fbe9e8,stroke:#d03b3b,color:#0b0b0b
```

> The red box is a deliberate callout: this is a **teaching-grade** isolation boundary (subprocess + resource limits + restricted builtins), not a production security boundary — see `ml/sandbox.py`'s module docstring and `docs/guide.html`'s limitations section for what a real deployment needs instead (E2B / container-per-execution / microVMs).

## 5. Tokenizer & Attention Explorer (`ml/tokenizer_explorer.py`, `routers/tokenizer.py`)

```mermaid
flowchart TD
    A["input text"] --> B["POST /api/tokenizer/explore"]
    B --> C["tokenizer_explorer.tokenize(text)\nGPT2Tokenizer.encode() -> token ids + decoded pieces"]
    B --> D["tokenizer_explorer.attention_weights(text, layer)\ntruncate to 40 tokens if longer"]
    D --> E["GPT2LMHeadModel(output_attentions=True)\nforward pass -> 12 layers x 12 heads x (seq, seq)"]
    E --> F["pick one layer -> average across the 12 heads\n-> a single (seq, seq) attention matrix"]
    C & F --> G["200 OK -> tokens, token_ids,\nattention matrix, layer, num_layers"]
    G --> H["Frontend renders:\ncolored token chips + an N x N attention heatmap"]
```

## 6. Admin Console (`routers/admin.py`)

```mermaid
flowchart TD
    A["Admin logs in (role=admin)"] --> B["GET /api/admin/system"]
    B --> C["COUNT(*) per table\n(users, meetings, search_queries, sandbox_runs, audit_logs)"]
    B --> D["model *._model is not None ?\n-> live loaded-status per AI model (5 local)"]
    B --> E["vectorstore.backend_name() + sandbox_provider\n+ shutil.disk_usage(data_dir)"]
    C & D & E --> F["system status JSON"]

    G["GET /api/admin/users"] --> H["list all users"]
    I["PATCH /api/admin/users/{id}"] --> J["toggle role or is_active"]
    K["GET /api/admin/audit-log"] --> L["last N AI-call records\n(who, action, model, latency, status)"]
```

## 7. Container bootstrap sequence (`main.py`)

```mermaid
sequenceDiagram
    autonumber
    participant D as Docker (docker compose up)
    participant U as Uvicorn / FastAPI
    participant BG as background thread
    participant GH as GitHub (jfk.flac) + HF (LibriSpeech dummy)
    participant FED as federalreserve.gov (FOMC minutes)
    participant HF as HuggingFace Hub

    D->>U: start container, run CMD
    U->>U: Base.metadata.create_all() (SQLite tables)
    U->>U: _seed_admin() (idempotent)
    U->>BG: spawn _warm_cache() thread
    U-->>D: /api/health responds 200 immediately

    Note over BG: each step below runs in its own\ntry/except (_warm_step) — an unrelated\nstep's failure never blocks the others.
    BG->>GH: ensure_sample_audio() [isolated step]
    GH-->>BG: jfk.flac + 5 LibriSpeech clips
    BG->>FED: index_fomc_minutes() -> ensure_fomc_minutes()\n+ chunk_text() + embed() + vectorstore.upsert() [isolated step]
    FED-->>BG: 7 real FOMC minutes documents, chunked + indexed
    BG->>HF: load embeddings, reranker, whisper, local_llm,\ntokenizer_explorer (5 independently-isolated steps)
    HF-->>BG: model weights (cached to named volume)
    BG->>U: log per-step result; "all warm" only if every step succeeded

    Note over D,U: GET /api/health/ready reports real per-model +\nper-step status; a failed dataset step self-heals\nthe next time a real request needs it.
```
