# CommerceIQ — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

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

## 2. Catalog Vision — image classification (`ml/vision.py`, `routers/vision.py`)

```mermaid
flowchart TD
    A["Upload photo OR pick a sample\n(Grocery Store Dataset, 20 images)"] --> B["POST /api/vision/classify\nor /classify-sample/{filename}"]
    B --> C["PIL.Image.open() + validate"]
    C --> D["vision._load()\nlazy-load ViTImageProcessor + ViTForImageClassification\n(WinKawaks/vit-tiny-patch16-224, cached after first call)"]
    D --> E["processor(image) -> pixel tensor"]
    E --> F["model(**inputs) -> logits"]
    F --> G["softmax + torch.topk(5)\n-> [{label, confidence}, ...]"]
    G --> H["save file to /app/data/uploads or reference sample path"]
    H --> I["INSERT catalog_items (SQLite)"]
    I --> J["embeddings.embed_passage(description)\n(intfloat/multilingual-e5-small)"]
    J --> K["vectorstore.upsert(id, text, vector, metadata)\n(Chroma, or cosine-fallback)"]
    K --> L["INSERT audit_logs\n(model, latency_ms)"]
    L --> M["200 OK -> {predictions, image_url, latency_ms}"]
```

## 3. Generative Studio — text-to-image (`ml/diffusion.py`, `jobs.py`, `routers/generate.py`)

```mermaid
flowchart TD
    A["prompt + steps + guidance_scale"] --> B["POST /api/generate"]
    B --> C["INSERT generated_images (status=queued)"]
    C --> D["jobs.submit(): spawn background thread\n(returns job_id immediately)"]
    D --> E["Frontend polls\nGET /api/generate/jobs/{job_id} every 2s"]

    subgraph BG["Background thread"]
        F["diffusion._load()\nlazy-load StableDiffusionPipeline\n(segmind/tiny-sd, safety_checker=None)"]
        F --> G["pipe(prompt, num_inference_steps, guidance_scale)"]
        G --> H["save PNG to /app/data/generated"]
        H --> I["UPDATE generated_images\n(status=done, image_path, duration)"]
        I --> J["INSERT audit_logs"]
    end

    D -.triggers.-> F
    J --> E
    E --> K{"status == done?"}
    K -- "queued/running" --> E
    K -- "failed" --> L["show job.error in UI"]
    K -- "done" --> M["render image + duration in gallery"]
```

## 4. Demand Forecasting & Anomaly Radar (`etl/online_retail.py`, `ml/forecast.py`, `ml/llm.py`)

```mermaid
flowchart TD
    A["horizon_days, use_openrouter, lang"] --> B["POST /api/forecast/run"]
    B --> C["ensure_online_retail_daily()"]
    C --> D{"cached parquet\nexists?"}
    D -- no --> E["download UCI Online Retail zip\n-> parse xlsx -> filter cancellations/refunds\n-> resample to daily revenue -> cache parquet"]
    D -- yes --> F["load cached daily series"]
    E --> F
    F --> G["forecast.run_forecast(series, horizon_days)"]
    G --> G1["ExponentialSmoothing(trend=add, seasonal=add, period=7)\n.fit() -> Holt-Winters model"]
    G1 --> G2["backtest: refit on all-but-last horizon,\nMAE always; MAPE excludes ~$0-actual days\n(see debug/issue-05) + sMAPE (always defined)"]
    G1 --> G3["seasonal_decompose() -> residuals\n|residual - mean| > 2.5*std -> anomalies"]
    G1 --> G4["forecast(horizon) + 95% CI\nfrom residual std"]
    G2 & G3 & G4 --> H["{history, forecast, anomalies, metrics, params}"]
    H --> I["llm.generate(system, user_msg, provider)\nprompt cites sMAPE (always sane) over\nraw MAPE (may be excluded/undefined)"]
    I --> J{"provider"}
    J -- "local (default)" --> K["Qwen2.5-0.5B-Instruct\napply_chat_template -> model.generate()"]
    J -- "openrouter (opt-in)" --> L["read api_keys/openrouter.md\n-> httpx POST openrouter.ai/api/v1/chat/completions\n(qwen/qwen3-8b)"]
    K --> M["business-readable insight text"]
    L --> M
    M --> N["INSERT forecast_runs + audit_logs"]
    N --> O["200 OK -> chart data + ai_insight"]
```

## 5. Semantic Catalog Search (`ml/embeddings.py`, `vectorstore.py`, `routers/search.py`)

```mermaid
flowchart TD
    A["natural-language query"] --> B["POST /api/search"]
    B --> C["embeddings.embed_query('query: ' + text)\n(intfloat/multilingual-e5-small, 384-dim)"]
    C --> D["vectorstore.query(vector, top_k)"]
    D --> E{"chromadb\navailable?"}
    E -- yes --> F["Chroma collection.query()\ncosine distance -> similarity = 1 - distance"]
    E -- no --> G["pure-Python cosine over\nin-memory fallback store"]
    F --> H["ranked [{id, text, metadata, similarity}]"]
    G --> H
    H --> I["INSERT audit_logs"]
    I --> J["200 OK -> results + backend name"]
```

## 6. Admin Console (`routers/admin.py`)

```mermaid
flowchart TD
    A["Admin logs in (role=admin)"] --> B["GET /api/admin/system"]
    B --> C["COUNT(*) per table\n(users, catalog_items, generated_images,\nforecast_runs, audit_logs)"]
    B --> D["model *._model / *._pipe is not None ?\n-> live loaded-status per AI model"]
    B --> E["vectorstore.backend_name()\n+ shutil.disk_usage(data_dir)"]
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
    participant HF as HuggingFace Hub
    participant UCI as UCI ML Repository
    participant GH as GitHub (GroceryStoreDataset)

    D->>U: start container, run CMD
    U->>U: Base.metadata.create_all() (SQLite tables)
    U->>U: _seed_admin() (idempotent)
    U->>BG: spawn _warm_cache() thread
    U-->>D: /api/health responds 200 immediately

    Note over BG: each step below runs in its own\ntry/except (_warm_step) — see debug/issue-06.\nOne step failing never blocks the others.
    BG->>UCI: ensure_online_retail_daily() (first run only)
    UCI-->>BG: online+retail.zip (22.6MB) [isolated step]
    BG->>GH: ensure_sample_images() (first run only)
    GH-->>BG: 20 sample product photos [isolated step]
    BG->>HF: load ViT-tiny, e5-small, Qwen2.5-0.5B, tiny-sd\n(4 independently-isolated steps, in that order)
    HF-->>BG: model weights (cached to named volume)
    BG->>U: log per-step result; "all warm" only if all 6 steps succeeded

    Note over D,U: docker-compose healthcheck polls /api/health\nthroughout — API is usable immediately.\nGET /api/health/ready reports real per-model +\nper-step status; a failed step self-heals the next\ntime a real request needs it (both ETL functions\nare idempotent/resumable).
```
