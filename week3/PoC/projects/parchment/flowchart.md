# Parchment — Function & Model Flowcharts

> Companion to [`architecture.md`](architecture.md). Also embedded in [`docs/guide.html`](docs/guide.html).
> Each diagram traces one feature end-to-end through the actual function names in `backend/app/`.

## 1. Authentication (`routers/auth.py`, `security.py`)

Identical to the Week1/11 PoCs — same JWT + bcrypt design, same shape-only email validator (not `EmailStr`, which broke `.local` admin logins in the Week1 PoC — see that project's `debug/issue-02`), reused here from the start rather than rediscovered.

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

## 2. Receipt Extraction — OCR vs. VLM side by side (`ml/ocr.py`, `ml/vlm.py`, `ml/llm.py`, `routers/receipts.py`)

```mermaid
flowchart TD
    A["Upload photo OR pick a synthetic sample"] --> B["POST /api/receipts/extract\nor /extract-sample/{filename}"]
    B --> C["ocr.image_to_text(image)\nTesseract LSTM engine"]
    C --> D["llm.generate(STRUCTURE_PROMPT, ocr_text, 'local')\nQwen2.5-0.5B -> JSON {vendor, items, total}"]
    D --> E{"JSON parses?"}
    E -- no --> F["ocr.regex_structure(ocr_text)\nfallback: regex item/total parser"]
    E -- yes --> G["structured fields"]
    F --> G
    B --> H["vlm.ask_image(image, question)\nSmolVLM-256M reads pixels directly, no OCR step"]
    G & H --> I["dedupe.register_and_check(ocr_text)\nembed (all-MiniLM-L6-v2) + compare vs Chroma"]
    I --> J["INSERT receipts (+ audit_logs)"]
    J --> K["200 OK -> OCR-path result + VLM-path result\n+ duplicate flag, shown side by side"]

    style H fill:#f3e3d0,stroke:#b5601f,color:#2b2016
```

> The highlighted box makes a common lesson literal: SmolVLM never runs OCR at all — it reads the image's pixels and answers directly, which is exactly the "pretrained multimodal AI" alternative to training a custom CNN.

## 3. PDF Summarization — with scanned-PDF OCR fallback (`etl/pdf_utils.py`, `ml/summarizer.py`, `routers/pdfs.py`)

```mermaid
flowchart TD
    A["Upload PDF OR use the sample\n(real Fed Monetary Policy Report)"] --> B["POST /api/pdfs/summarize\nor /summarize-sample"]
    B --> C["pdf_utils.extract_text(path)\npypdf PdfReader.extract_text() per page"]
    C --> D{"extracted chars >= threshold?"}
    D -- "yes (normal PDF)" --> E["text ready"]
    D -- "no (likely scanned/image-only)" --> F["pdf2image.convert_from_path()\n-> render each page to PNG"]
    F --> G["ocr.image_to_text(page_image)\nreuses the SAME Tesseract engine as Receipts"]
    G --> E
    E --> H["summarizer.summarize_long_text(text)\nchunk_text() -> distilbart per chunk -> combine -> distilbart again\n(map-reduce, the standard technique for long documents)"]
    H --> I["summarizer.numeric_cross_check(summary, source_text)\nevery number the summary states must appear in the source"]
    I --> J["dedupe.register_and_check(text)"]
    J --> K["INSERT pdf_summaries (+ audit_logs)"]
    K --> L["200 OK -> summary + numeric_check_passed + duplicate flag"]

    style F fill:#f3e3d0,stroke:#b5601f,color:#2b2016
    style G fill:#f3e3d0,stroke:#b5601f,color:#2b2016
```

## 4. HTML Table Parsing (`etl/html_utils.py`, `routers/tables.py`)

```mermaid
flowchart TD
    A["URL (user-entered or the Wikipedia sample)"] --> B["POST /api/tables/parse"]
    B --> C["httpx.get(url) with an identifying User-Agent\n(standard scraping-etiquette practice)"]
    C --> D["BeautifulSoup(html, 'html.parser')\nfind_all('table')"]
    D --> E["per table: find_all('tr') -> th/td text\npad/truncate rows to uniform width"]
    E --> F["pandas.DataFrame(rows, columns=headers)"]
    F --> G["INSERT html_scrapes (+ audit_logs)"]
    G --> H["200 OK -> headers + rows + row_count + CSV string\n(no AI model in this path — deterministic parsing doesn't need one)"]
    H --> I["Frontend: table preview + 'Download CSV' button"]
```

## 5. Document Library — near-duplicate detection, not RAG (`ml/dedupe.py`, `routers/library.py`)

```mermaid
flowchart TD
    A["A receipt or PDF is processed"] --> B["embeddings.embed(text)\nall-MiniLM-L6-v2, same model reused from the Week2 PoC"]
    B --> C["vectorstore.query(vector, top_k=3)\nsearch existing Chroma entries of the SAME doc_type"]
    C --> D{"best match similarity\n>= dedupe_similarity_threshold (0.90)?"}
    D -- yes --> E["flag as duplicate: {duplicate_of, similarity}"]
    D -- no --> F["not a duplicate"]
    E & F --> G["vectorstore.upsert(doc_id, text, vector, metadata)\n(so future documents can compare against this one too)"]
    G --> H["GET /api/library shows every document,\nduplicate flags surfaced directly"]

    style D fill:#fbe3df,stroke:#c1622f,color:#2b2016
```

> This is the entire vector-DB feature's scope: one similarity check per new document, never a "search my documents" UI and never text fed back into an LLM's context. Full retrieve-then-answer search over this same corpus is deliberately left out of scope as a separate, future feature — see `architecture.md` §4.

## 6. Admin Console (`routers/admin.py`)

```mermaid
flowchart TD
    A["Admin logs in (role=admin)"] --> B["GET /api/admin/system"]
    B --> C["COUNT(*) per table\n(users, receipts, pdf_summaries, html_scrapes, audit_logs)"]
    B --> D["model *._model/_pipeline is not None ?\n-> live loaded-status per AI model (5 local)"]
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
    participant FED as federalreserve.gov (sample PDF)
    participant HF as HuggingFace Hub

    D->>U: start container, run CMD
    U->>U: Base.metadata.create_all() (SQLite tables)
    U->>U: _seed_admin() (idempotent)
    U->>BG: spawn _warm_cache() thread
    U-->>D: /api/health responds 200 immediately

    Note over BG: each step below runs in its own\ntry/except (_warm_step) — an unrelated\nstep's failure never blocks the others.
    BG->>BG: ensure_sample_receipts() [isolated step, no network]
    BG->>FED: ensure_sample_pdf() [isolated step]
    FED-->>BG: Fed Monetary Policy Report PDF
    BG->>BG: check tesseract binary [isolated step, no network]
    BG->>HF: load SmolVLM, Qwen2.5-0.5B, distilbart,\nall-MiniLM-L6-v2 (4 independently-isolated steps)
    HF-->>BG: model weights (cached to named volume)
    BG->>U: log per-step result; "all warm" only if every step succeeded

    Note over D,U: GET /api/health/ready reports real per-model +\nper-step status; a failed sample-data step self-heals\nthe next time a real request needs it.
```
