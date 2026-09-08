# Verity — Architecture

> Week5_1 PoC_v2 · Grounded Claims-Research Assistant for Fenwick Mutual
> This document is also embedded (with the same diagrams) inside [`docs/guide.html`](docs/guide.html).

## 1. System overview

Verity is a single-container full-stack application: a React (TypeScript) SPA served as static
files by a FastAPI backend, hosting three local AI models plus one optional cloud escalation model
behind a REST + streaming API, backed by SQLite (structured data) and Chroma (vector data). The
structural shape is the same proven pattern as every earlier product in this series — what's different
this round is the depth of commercial-grade hardening applied to it (§4) and a fully fictional,
never-live-web claims research corpus (§2 in the README, `search/jurisdictions.py`).

```mermaid
flowchart TB
    subgraph Client["Browser"]
        SPA["React SPA<br/>Fenwick Ledger design system<br/>EN default / KO, light default / dark"]
    end

    subgraph Container["Docker container — verity (single image, one exposed port)"]
        API["FastAPI application (Python 3.11, Uvicorn)"]
        AUTH["Auth: access+refresh JWT (httpOnly cookies),<br/>CSRF double-submit, account lockout"]
        RATE["rate_limit.py — in-memory sliding window"]
        AUDIT["audit.py — hash-chained AuditLog"]
        METRICS["metrics.py — real p50/p95/p99"]

        subgraph Models["AI models (lazy-loaded singletons)"]
            EMB["① multilingual-e5-small<br/>rerank + library embedding"]
            RRK["② ms-marco-MiniLM-L-6-v2<br/>cross-encoder reranker"]
            LLM["③ Qwen2.5-0.5B-Instruct<br/>quick answer / precedent brief / radar"]
            OR["④ qwen/qwen3-8b via OpenRouter<br/>(opt-in, budget-gated)"]
        end

        GROUND["groundedness.py + ghost_citation.py<br/>(URL check + entity-hallucination check)"]
        FRAUD["fraud_signals.py — keyword-only taxonomy match"]

        subgraph Storage["Storage (Docker named volumes)"]
            SQL[("SQLite<br/>organizations · users · refresh_tokens ·<br/>research_sessions · report_entries · cat_events ·<br/>budget_settings · audit_logs (hash-chained) · error_logs")]
            VDB[("Chroma PersistentClient<br/>past-report embeddings")]
            HFCACHE[("HuggingFace model cache")]
        end

        API --> AUTH --> RATE
        API --> METRICS
        API --> EMB & RRK & LLM
        API --> GROUND
        API --> FRAUD
        API -.opt-in, budget-gated.-> OR
        API --> AUDIT
        API --> SQL
        API --> VDB
        EMB & RRK & LLM -.weights.-> HFCACHE
    end

    subgraph External["External"]
        ORAPI["OpenRouter API"]
        WEB[("Live web — Vendor Radar ONLY,<br/>never claims research")]
    end

    subgraph Secrets["Read-only host mount"]
        KEYFILE["api_keys/openrouter.md"]
    end

    SPA <-->|"HTTPS + JSON, httpOnly cookies,<br/>fetch() + ReadableStream"| API
    OR -->|"httpx POST /chat/completions"| ORAPI
    OR -.reads at call-time.-> KEYFILE
    API -->|"radar evaluation only"| WEB

    style Models fill:#1f4d3d1a,stroke:#1f4d3d,color:#241f18
    style Storage fill:#a85d2e1a,stroke:#a85d2e,color:#241f18
    style External fill:#a83a2e1a,stroke:#a83a2e,color:#241f18
```

## 2. Engineering depth — genuinely more advanced than a typical first-pass implementation

A typical first-pass, naive implementation of this pattern (search-API + reranking +
search-grounded generation) is often a simple Streamlit app whose default synthesis path calls
**no LLM at all** (a rule-based template that just lists reranked snippets, sometimes justified as
"structurally zero hallucination risk" since it never generates new text). The comparison below is
against that kind of baseline:

| Dimension | Typical baseline implementation | Verity |
|---|---|---|
| Answer generation | No LLM call by default — a rule-based template lists reranked snippets | A real LLM (local or OpenRouter) synthesizes a cited Quick Answer or structured Precedent Brief every time, streamed token by token |
| Persistence | None — stateless, single-shot | SQLite + Chroma, both `org_id`-scoped, both survive restarts |
| Verification | None (the rule-based path has nothing to verify) | Citation-marker validity + content-similarity groundedness + URL ghost-citation check + **entity-hallucination cross-check** (a real gap this build found and mitigated, see `debug/issue-03`) |
| Target/positioning | No stated target audience in a typical baseline's framing | A named persona (Dana Whitfield), a named fictional company, and a landing page that states both explicitly |
| Auth/security | None | Access+refresh JWT rotation, CSRF, account lockout, rate limiting, tamper-evident audit log — none of which any earlier product in this series (including this project's own predecessor, Compass) implemented |
| Observability | None | Real p50/p95/p99 latency, structured error log, public status page |

This isn't a criticism of that kind of baseline — a first-pass build like that is naturally scoped
for a quick, time-boxed exercise. Verity is scoped as a demonstration of what a genuinely commercial
version of the same underlying idea (search-API + reranking + search-grounded generation) looks like
once built out with a real target customer and a real security/observability bar in mind.

## 3. Design — "Fenwick Ledger," a shared suite identity

This round's request asked for a completely different approach from Weeks 10-13 and this project's
own prior Compass build, at a materially higher quality bar, with an explicitly named target — and
for Week5_1 and Week5_2 to read as one connected company's product suite rather than two
independent weekly identities. Five prior distinct visual identities already exist in this
project series (cool-gray/blue sidebar; warm parchment/terracotta top-tabs; glass/gradient-mesh floating
sidebar; navy/brass/teal command-console; pastel lilac/sage claymorphism) — "Fenwick Ledger" is a
sixth, sharing across Verity and Threshold (its Week5_2 companion) rather than repeating any
existing axis:

- **Color**: deep bottle-green (`#1f4d3d` light / `#4f9c7f` dark) as Verity's primary accent, copper
  (`#a85d2e` light / `#d18a53` dark) as the suite's shared interaction color (and Threshold's own
  primary), on a warm ivory/bone ground (light) or espresso-charcoal (dark, not navy or purple) —
  evoking an underwriting ledger's precision and permanence rather than a "chart room" or pastel-soft
  register.
- **Type**: **Fraunces** (a warm, high-contrast display serif with ink-trap detailing) for headings,
  **IBM Plex Sans** for UI body, **IBM Plex Mono** with tabular figures for claim numbers, policy
  IDs, and monetary amounts — none of the three used in any prior week.
- **Navigation**: a **dossier tab-binder** — a left-anchored vertical stack of overlapping,
  manila-style tab dividers that "pull forward" (translate + shadow lift) on selection while the
  others recede — a distinct metaphor from every prior nav pattern in this project series, and one
  grounded directly in the subject matter: pulling a case file from a binder.

**Accessibility, measured not assumed**: running text uses `--text-primary`/`--text-secondary`
(16.09:1 / 7.87:1 light, 13.66:1 / 9.07:1 dark against their surfaces — computed via the same Python
WCAG contrast-ratio script used every prior week); `--text-muted` (used only for captions/timestamps,
never body copy) sits at 3.75:1/4.62:1; accent colors clear 4.5:1+ in both themes despite being
restricted to icons/borders/headings by design convention.

## 4. Commercial-grade engineering — what was actually added, and its real scope boundary

| Area | What's implemented | Explicit scope boundary |
|---|---|---|
| **Tenancy** | `Organization` table, every other table FK'd to `org_id` instead of a hardcoded `id=1` singleton | No tenant-switcher UI; exactly one org is seeded |
| **Session security** | Short-lived access JWT (20 min) + rotating refresh token (7 day, single-use, SHA-256-hashed at rest), httpOnly/SameSite=Strict cookies, CSRF double-submit on every mutating request, lockout after 5 failed logins (15 min) | `COOKIE_SECURE`/`ENFORCE_SECURE_DEFAULTS` default off so the demo boots with its own documented credentials over plain HTTP, exactly like every prior PoC — a real deployment behind TLS flips both |
| **Audit integrity** | Hash-chained `AuditLog` (`entry_hash = sha256(prev_hash‖content)`); admin "Verify integrity" walks the chain and reports the exact break point | Single-writer chain — a real multi-instance deployment would need a coordinated append (e.g. a single audit-writer service) to keep one linear chain |
| **Rate limiting** | Hand-rolled in-memory sliding window on auth + AI endpoints | Explicitly single-process; a real multi-instance deployment needs shared state (Redis or similar) |
| **Observability** | Real per-route p50/p95/p99 (rolling window), structured `ErrorLog` with request-correlation IDs, public `/api/status` | In-memory metrics reset on restart — documented, not hidden |
| **UX** | Public marketing landing page, empty states, skeleton-free direct loading states, keyboard focus rings, tablet-responsive minimum | No onboarding tour/wizard — deferred as a lower-priority polish item |

## 5. Data flow — a Precedent Brief request

```mermaid
sequenceDiagram
    autonumber
    participant U as User (browser)
    participant FE as React SPA
    participant API as FastAPI
    participant JUR as jurisdictions.py (fictional corpus)
    participant RRK as rerank_pipeline.py
    participant LLM as Qwen2.5-0.5B (streaming)
    participant CHK as groundedness + ghost_citation (+entities) + fraud_signals
    participant DB as SQLite
    participant VDB as Chroma

    U->>FE: asks a claims question, selects "Precedent brief" + a jurisdiction
    FE->>API: POST /api/research/query (streamed, CSRF header attached)
    API->>JUR: search(query, jurisdiction) — deterministic, offline
    JUR-->>API: candidate fictional documents
    API->>RRK: rerank_results() — bi-encoder + cross-encoder
    RRK-->>API: top-k sources
    API->>LLM: stream_generate(BRIEF_SYSTEM_PROMPT, sources+question)
    loop token stream
        LLM-->>API: text fragment
        API-->>FE: SSE "data: {delta}"
    end
    API->>CHK: verify(report, sources) + check(report, urls) + check_entities(report, sources) + fraud check
    CHK-->>API: {groundedness, ghost_citations incl. unverified_entities, fraud_signals}
    API->>DB: INSERT report_entries (org-scoped)
    API->>VDB: upsert(embed(question+answer)) — Library semantic search
    API-->>FE: SSE "data: {done, entry: {...}}"
    FE-->>U: structured brief + source-trust badges + fraud-signal panel rendered
```

## 6. Storage model

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ RESEARCH_SESSIONS : has
    ORGANIZATIONS ||--o{ CAT_EVENTS : has
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--o{ AUDIT_LOGS : generates
    RESEARCH_SESSIONS ||--o{ REPORT_ENTRIES : contains
    CAT_EVENTS ||--o{ RESEARCH_SESSIONS : tags

    ORGANIZATIONS {
        int id PK
        string name
        text licensed_jurisdictions_json "fictional jurisdiction codes"
    }
    USERS {
        int id PK
        int org_id FK
        string email UK
        int failed_login_attempts
        datetime locked_until
    }
    REFRESH_TOKENS {
        int id PK
        int user_id FK
        string token_hash "sha256, never plaintext"
        datetime expires_at
        datetime revoked_at
    }
    REPORT_ENTRIES {
        int id PK
        int session_id FK
        string mode "quick|precedent_brief|radar"
        text brief_json
        text source_trust_json
        text ghost_citations_json "incl. unverified_entities"
        text fraud_signals_json
        float groundedness_score
    }
    AUDIT_LOGS {
        int id PK
        string prev_hash
        string entry_hash "sha256(prev_hash + content)"
        float latency_ms "real, measured"
    }
```

## 7. Production / cloud scaling — what would change

Same shape as every prior PoC's own scaling table (app-tier replication, managed Postgres, a
managed vector DB, GPU burst capacity for the local LLM) — plus items specific to this round's new
subsystems: a shared-state rate limiter (Redis) for multi-instance deployment, a real metrics
backend (Prometheus/Grafana) rather than the in-memory rolling window, and a coordinated
single-writer path for the audit-log hash chain if the API tier is ever horizontally scaled.

### Estimated monthly cost at small commercial scale
(~500 DAU, ~1.5k research queries/day; indicative Aug 2026 list prices)

| Item | Assumption | Est. monthly cost |
|---|---|---|
| App hosting (2 vCPU/4GB) | 1-2 instances | $70–140 |
| Managed Postgres | 1 instance + backup | $60–90 |
| Managed vector DB / pgvector | usage-based | $0–50 |
| GPU burst (local LLM) | ~15 GPU-hours/mo | $10–25 |
| OpenRouter (opt-in escalation) | ~10% of queries | $2–8 |
| Redis (rate limiting, multi-instance) | small managed instance | $10–20 |
| Metrics/logging | basic managed tier | $10–30 |
| **Total (indicative)** | | **≈ $162 – 363/month** |

## 8. Deployment considerations

Same core list as every prior PoC (environment parity, secrets via a real secret manager, Postgres +
migrations, CORS restricted to the real origin, no proxy buffering on streaming endpoints) — plus:
**flip `ENFORCE_SECURE_DEFAULTS` and `COOKIE_SECURE` to `true`** behind real TLS (the demo ships both
off so it boots with its own documented credentials over plain HTTP); **move rate limiting and
metrics to shared backends** before running more than one instance, since both are currently
single-process, in-memory state by design.
