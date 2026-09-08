# VoxIQ — Architecture

> AI Meeting & Knowledge Intelligence Platform
> This document is also embedded (with the same diagrams) inside [`docs/guide.html`](docs/guide.html).

## 1. System overview

VoxIQ is a single-container full-stack application: a React (TypeScript) single-page app served as static files by a FastAPI backend, which hosts six AI models (five local, one optional cloud) behind a REST API, backed by SQLite (structured data) and Chroma (vector data) — the same proven shape as an earlier product in this series, CommerceIQ, applied to VoxIQ's own four technical pillars (embeddings/reranking, audio ASR, code-execution sandboxing, LLM internals).

```mermaid
flowchart TB
    subgraph Client["Browser"]
        SPA["React SPA<br/>(TypeScript · Vite · Tailwind)<br/>i18n: EN default / KO<br/>Theme: Light default / Dark"]
    end

    subgraph Container["Docker container — voxiq (single image, one exposed port)"]
        API["FastAPI application<br/>(Python 3.11, Uvicorn)"]
        AUTH["Auth<br/>JWT + bcrypt<br/>cookie or Bearer"]

        subgraph Models["AI models (lazy-loaded singletons)"]
            EMB["① all-MiniLM-L6-v2<br/>bi-encoder embeddings"]
            RRK["② ms-marco-MiniLM-L-6-v2<br/>cross-encoder reranker"]
            ASR["③ Whisper (tiny)<br/>speech-to-text"]
            QWEN["④ Qwen2.5-0.5B-Instruct<br/>local code-gen agent"]
            TOK["⑤ GPT-2<br/>tokenizer + attention explorer"]
            OR["⑥ qwen/qwen3-8b<br/>via OpenRouter API<br/>(opt-in, cloud)"]
        end

        SANDBOX["Local code sandbox<br/>(subprocess + resource limits +<br/>restricted builtins — teaching-grade,<br/>NOT a production security boundary)"]

        subgraph Storage["Storage (Docker named volumes)"]
            SQL[("SQLite<br/>users · meetings · search_queries · sandbox_runs · audit_logs")]
            VDB[("Chroma vector store<br/>FOMC minutes (chunked) + meeting transcripts")]
            FILES[("Uploaded / sample audio<br/>+ downloaded FOMC minutes")]
            HFCACHE[("HuggingFace + Whisper model cache")]
        end

        API --> AUTH
        API --> EMB & RRK & ASR & QWEN & TOK
        API --> SANDBOX
        API -.opt-in.-> OR
        API --> SQL
        API --> VDB
        API --> FILES
        EMB & RRK & ASR & QWEN & TOK -.weights.-> HFCACHE
    end

    subgraph External["External (opt-in only)"]
        ORAPI["OpenRouter API<br/>openrouter.ai"]
    end

    subgraph Secrets["Read-only host mount"]
        KEYFILE["api_keys/openrouter.md<br/>(never baked into the image,<br/>never hardcoded)"]
    end

    SPA <-->|"HTTPS/JSON<br/>fetch() + JWT"| API
    OR -->|"httpx POST /chat/completions"| ORAPI
    OR -.reads at call-time.-> KEYFILE

    style Models fill:#e7f0fc,stroke:#2a78d6,color:#0b0b0b
    style Storage fill:#f6f6f4,stroke:#c3c2b7,color:#0b0b0b
    style External fill:#fde9e9,stroke:#d03b3b,color:#0b0b0b
```

## 2. Why this stack

| Choice | Reasoning |
|---|---|
| **Same FastAPI + React template as CommerceIQ** | A proven, already-hardened architecture (auth, admin, Docker, readiness probing, isolated bootstrap steps) is reused deliberately rather than reinvented — see §5 for the specific hardening carried over. |
| **A "meeting intelligence" product, not 4 disconnected demo tabs** | Embeddings/reranking, audio ASR, code sandboxes, and tokenization are often taught and demoed as separate, disconnected topics; VoxIQ ties them into one coherent workflow a real ops/knowledge team would use: record → transcribe → search → analyze. |
| **Real FOMC meeting minutes as the search corpus** | Generic filler text doesn't demonstrate anything; these are literally real meeting minutes (U.S. Federal Reserve, public domain), giving the "Knowledge Search" feature genuine, substantive content to search — and a legitimate reason to need chunking (each document is ~9,000 words). |
| **Cross-encoder reranking shown side-by-side, not just applied silently** | The bi-encoder vs. cross-encoder trade-off is best taught through a concrete before/after example; the UI reproduces that directly instead of hiding it behind a single "smart search" box. |
| **Local sandbox as the default, E2B scaffolded only** | This project has no E2B API key; per the brief's "cloud API only when actually available and needed," the local subprocess-based sandbox (a common "local fallback" design for this kind of feature) is the default and only validated execution path. |
| **5 local models + 1 optional cloud model** | All five local models (MiniLM bi-encoder, MiniLM cross-encoder, Whisper-tiny, Qwen2.5-0.5B, GPT-2) are well-established, widely-used choices for their respective tasks — no new, unvalidated choices. OpenRouter's `qwen/qwen3-8b` is the one cloud path, opt-in and validated with a real key this round. |

## 3. Data flow — one representative request (Knowledge Search)

```mermaid
sequenceDiagram
    autonumber
    participant U as User (browser)
    participant FE as React SPA
    participant API as FastAPI
    participant EMB as all-MiniLM-L6-v2 (bi-encoder)
    participant VDB as Chroma vector store
    participant RRK as ms-marco-MiniLM-L-6-v2 (cross-encoder)
    participant DB as SQLite

    U->>FE: types a query, clicks "Search"
    FE->>API: POST /api/search { query, top_k }
    API->>EMB: embed(query)
    EMB-->>API: query vector
    API->>VDB: query(vector, top_k*3)  // over-fetch candidates
    VDB-->>API: candidate chunks (FOMC minutes + meeting transcripts)
    Note over API: bi_encoder_results = candidates[:top_k]  (pure ANN order)
    API->>RRK: rerank(query, candidate texts)
    RRK-->>API: one relevance score per candidate
    Note over API: cross_encoder_results = re-sorted by that score
    API->>DB: INSERT search_queries (+ audit_logs)
    API-->>FE: JSON { bi_encoder_results, cross_encoder_results, top1_changed }
    FE-->>U: two ranked lists side-by-side + "did reranking change #1?"
```

## 4. Storage model

```mermaid
erDiagram
    USERS ||--o{ MEETINGS : owns
    USERS ||--o{ SEARCH_QUERIES : owns
    USERS ||--o{ SANDBOX_RUNS : owns
    USERS ||--o{ AUDIT_LOGS : generates

    USERS {
        int id PK
        string email UK
        string hashed_password
        string role "user | admin"
        bool is_active
    }
    MEETINGS {
        int id PK
        int owner_id FK
        string source "upload | sample"
        text transcript
        string detected_language
        float transcribe_latency_ms
    }
    SEARCH_QUERIES {
        int id PK
        int owner_id FK
        text query_text
        text bi_results_json
        text cross_results_json
        bool top1_changed
    }
    SANDBOX_RUNS {
        int id PK
        int owner_id FK
        text request_text
        text generated_code
        text stdout
        string status "queued|running|done|failed"
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string model_used
        float latency_ms
    }
```

Meeting transcripts and FOMC-minutes chunks are additionally embedded (`all-MiniLM-L6-v2`) and upserted into a **Chroma** collection — the SQL rows are the system of record, the vector store is a derived search index, the same "record + index" split used in Week1's CommerceIQ.

## 5. Hardening carried over from the Week1 PoC (applied from day one here)

Rather than rediscover the same classes of bug, VoxIQ's initial build already incorporates every fix the Week1 PoC needed a follow-up pass to find:

| Week1 finding | Applied here from the start |
|---|---|
| Deliverability-checking `EmailStr` broke `.local` admin logins | Auth uses the same shape-only email regex validator, not `EmailStr` |
| Cold-start feature timeouts looked like bugs | `GET /api/health/ready` + a `verify_e2e.py` wait-for-warm step exist from the first build |
| One failed bootstrap step silently skipped the others | `_warm_step()` isolates each of the 6 startup steps (2 datasets + hosting the FOMC index + 5 models... see main.py) from the start |
| `run.sh` needlessly recreated an already-running container | The "already running? just report the URL" check is in `run.sh` from the start |
| No repo-root `.gitignore` protecting `api_keys/` | Already exists at the repo root (added during the Week1 follow-up) — nothing new needed here |

## 6. Production / cloud scaling — what would change

Same shape as Week1's CommerceIQ (see that PoC's `architecture.md` §5 for the full table and diagram) — app-tier replication, managed Postgres, a managed/scaled vector DB, object storage + CDN for audio files, a GPU node pool for Whisper/reranking at volume, and — specific to VoxIQ — **replacing the local sandbox with E2B or an equivalent managed, genuinely-isolated code-execution service** before ever exposing the Analytics Agent to untrusted users at scale; the local subprocess sandbox here is explicitly a teaching-grade boundary, not a production one (see `docs/guide.html`'s limitations section).

### Estimated monthly cost at small commercial scale
(~500 daily active users, ~3k AI calls/day across all features; figures below are indicative public list prices as of Aug 2026 — always re-check current provider pricing before budgeting for real)

| Item | Assumption | Est. monthly cost |
|---|---|---|
| App hosting (Cloud Run / Fargate, 2 vCPU / 4GB) | 1–2 instances, always-on for warm models | $70–140 |
| Managed Postgres | 1 instance + daily backup | $60–90 |
| Managed vector DB (pgvector on same Postgres, or a managed service) | pgvector: $0 extra / managed: usage-based | $0–50 |
| Object storage + CDN (audio files) | ~30GB audio, moderate egress | $8–20 |
| Managed code-execution sandbox (E2B or equivalent, replacing the local one) | ~500 analytics runs/day | $30–80 |
| OpenRouter (`qwen/qwen3-8b`, opt-in code-gen only) | ~100k tokens/day @ $0.117/$0.455 per M | $8–20 |
| Monitoring/logging | Basic managed tier | $0–20 |
| **Total (indicative)** | | **≈ $175 – 420 / month** |

## 7. Deployment considerations

Same core list as Week1's CommerceIQ (environment parity via the same Dockerfile, secrets via a real secret manager instead of a file mount, Postgres + alembic migrations, CORS restricted to the real frontend origin) — with one VoxIQ-specific addition: **the local code sandbox must be replaced before any real deployment that lets untrusted users control the analysis request text**, since a sufficiently motivated user could craft an LLM prompt designed to make the generated code attempt something the restricted-builtins boundary doesn't actually stop (documented plainly in `docs/guide.html`'s limitations section, in the same spirit of being upfront about what a local-fallback sandbox is not).
