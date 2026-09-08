# Glossary & Model Cards — Parchment

## AI models used

### 1. Tesseract (LSTM OCR engine, via `pytesseract`)
- **What it is**: an open-source OCR engine; version 4+ uses an LSTM (recurrent neural network) recognition engine internally rather than the older pattern-matching approach, making it a genuine neural OCR model, not just a classical algorithm.
- **Why chosen**: a common default, no-key-required image-reading path for this kind of task.
- **How Parchment uses it**: the Receipts tab's "classic" path — reads an image's text, which is then structured into fields by regex or the local LLM. Also reused (cross-feature) as the scanned-PDF OCR fallback in the PDF Summarizer tab.
- **Card**: <https://github.com/tesseract-ocr/tesseract>

### 2. HuggingFaceTB/SmolVLM-256M-Instruct (local vision-language model)
- **What it is**: a 256M-parameter multimodal model (a 93M vision encoder + the 135M SmolLM2 language model) — documented as "the smallest multimodal model in the world," explicitly designed for on-device/CPU-feasible inference.
- **Why chosen**: verified to exist and match this project's CPU-only, no-API-key requirement before being chosen; embodies a common lesson ("use a pretrained multimodal model instead of training your own CNN") with a real, running local model rather than only narrating the idea.
- **How Parchment uses it**: the Receipts tab's second path — reads the receipt image directly and answers a question about it, with no separate OCR step, shown side by side with the Tesseract+structuring path.
- **Card**: <https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct>

### 3. Qwen/Qwen2.5-0.5B-Instruct (local structuring/insight LLM)
- **What it is**: a 494M-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: the exact small local LLM validated/reused in the Week1 and Week2 PoCs for fully offline, no-API-key text generation.
- **How Parchment uses it**: turns raw OCR text into structured JSON fields (vendor/items/total) for the Receipts tab, and writes short insight text where relevant. Falls back to a regex parser if its JSON output doesn't parse.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 4. sshleifer/distilbart-cnn-12-6 (local summarization model)
- **What it is**: a 306M-parameter distilled BART model, fine-tuned on the CNN/DailyMail summarization dataset, Apache-2.0 licensed.
- **Why chosen**: verified to exist on the HuggingFace Hub before being chosen; a genuine upgrade over a naive plain word-frequency rule-based summarizer, while staying 100% local.
- **How Parchment uses it**: the PDF Summarizer tab's default path — long documents are chunked (word-count with overlap) and summarized map-reduce style (per-chunk, then combined and summarized once more).
- **Card**: <https://huggingface.co/sshleifer/distilbart-cnn-12-6>

### 5. sentence-transformers/all-MiniLM-L6-v2 (duplicate-detection embeddings)
- **What it is**: a 6-layer MiniLM sentence-embedding model, ~22.7M parameters, 384-dim output.
- **Why chosen**: the exact bi-encoder validated/reused in the Week2 PoC's Knowledge Search feature; here repurposed for a narrower task.
- **How Parchment uses it**: embeds every processed receipt/PDF's text and checks it against everything already in the Chroma vector store, flagging near-duplicates above a similarity threshold — a duplicate-detection feature, deliberately not a search/RAG feature (see `architecture.md` §4 for why that distinction is scoped this way).
- **Card**: <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2>

### 6. qwen/qwen3-8b via OpenRouter (optional cloud upgrade)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API.
- **Why chosen**: cheap (verified live pricing during the Week1 PoC build, reused here), and the project brief specifically asks for an OpenRouter-validated cloud path this round.
- **How Parchment uses it**: strictly opt-in (a checkbox on the PDF Summarizer page) alternative to the local `distilbart` summarizer.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

### Scaffolded, not validated this round
- **Gemini** (`google-genai`, model id `gemini-2.5-flash`) — a common, well-documented choice for image/document extraction tasks like this one. Named explicitly here for parity, but per this build's brief, OpenRouter is the only validated cloud API this round; calling the Gemini config path raises `NotImplementedError`.
- **OpenAI, Anthropic** — config fields exist (`ml/llm.py`), not implemented.

## Key terms

| Term | Meaning in this project |
|---|---|
| **OCR vs. VLM** | OCR (Optical Character Recognition) reads pixels into *text* — it has no understanding of what the text means. A vision-language model (VLM) reads pixels and directly answers a *question* about the image's content, without a separate text-extraction step. Parchment's Receipts tab runs both on the same image so the difference is visible, not just described. |
| **Map-reduce summarization** | Splitting a document too long for one model pass into overlapping chunks, summarizing each chunk independently ("map"), then summarizing the combined partial summaries once more ("reduce") — the standard technique for handling long documents, applied here with the `distilbart` model. |
| **Numeric cross-check** | The discipline "a summary is a reference, numbers must come from the source," made concrete: every distinct number Parchment's summary states is checked against the literal source text, and any that can't be found is flagged rather than silently trusted. |
| **Near-duplicate detection (not RAG)** | Embedding a document and comparing it against previously-seen documents to flag likely re-submissions — a single similarity check, not a search interface, and never used to feed an LLM's context window. Full retrieve-then-answer search (RAG) over a document corpus is a substantial feature of its own; Parchment deliberately stops short of building it here. |
| **Scanned PDF fallback** | A PDF with no extractable text layer (just page images) is detected automatically (extracted character count below a threshold) and routed through `pdf2image` (page-to-image rendering) + the same Tesseract OCR engine used in the Receipts tab — a common real-world scenario, implemented here rather than only explained. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call is recorded with who made it, which model, how long it took, and whether it succeeded, mirroring the pattern reused from the Week1/11 PoCs. |
