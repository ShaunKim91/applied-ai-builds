# Data sources

All three sample sources below are prepared automatically — you never need
to do this by hand. `backend/app/main.py`'s startup hook calls the same
functions shown here in a background thread on first boot;
`scripts/download_data.sh` is a manual trigger if you ever want to force a
re-check.

## 1. Synthetic sample receipts — Receipts tab

- **Source**: generated in-process by `backend/app/etl/sample_receipts.py`, using a small, standard image-generation technique: a Pillow-drawn image with `ImageFont.load_default(size=22)` (no external font file needed).
- **Why synthetic, not real receipts**: real receipt photos carry real PII (names, card numbers, addresses) — a well-known risk with this kind of demo data. Rather than source real receipts (a licensing *and* privacy problem), this project draws its own, clearly-labeled-as-synthetic demo receipts, sidestepping the issue entirely.
- **License**: none needed — 100% original, generated content, no third-party material involved.
- **What Parchment does with it**: `ensure_sample_receipts()` renders 3 varied demo receipts (a cafe, an office-supply store, a hardware store) to `data/sample_receipts/` once, offered as one-click "try a sample" buttons on the Receipts page.

## 2. Sample PDF — PDF Summarizer tab

- **Source**: Board of Governors of the Federal Reserve System, *Monetary Policy Report* (semiannual report to Congress)
  <https://www.federalreserve.gov/monetarypolicy/publications/mpr_default.htm>
- **Direct download** (verified reachable before being hardcoded): <https://www.federalreserve.gov/monetarypolicy/files/20240705_mprfullreport.pdf> (July 5, 2024 edition)
- **License**: an official publication of a U.S. federal instrumentality — public domain under U.S. copyright law (17 U.S.C. §105), the same public-domain reasoning already applied to the FOMC minutes used in the Week2 PoC.
- **What Parchment does with it**: `ensure_sample_pdf()` downloads it once to `data/sample_pdf/`, offered as a one-click "try the sample report" option on the PDF Summarizer page. If the download fails (e.g. offline), the app degrades gracefully — the sample button is simply hidden; uploading your own PDF still works.
- **Download it yourself** (outside the app, for inspection): `curl -o mpr.pdf https://www.federalreserve.gov/monetarypolicy/files/20240705_mprfullreport.pdf`

## 3. Sample HTML page — HTML Tables tab

- **Source**: Wikipedia, *List of countries by GDP (nominal)*
  <https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)>
- **License**: CC BY-SA 4.0 (Wikipedia contributors). This page is fetched live and parsed on demand — it is never bundled/redistributed as a stored dataset — but is credited here per the license's attribution requirement.
- **Verified structure** (before being hardcoded as the default sample): the page contains real `<table>` elements with columns for Country/Territory and GDP estimates from the IMF, World Bank, and UN, across ~190+ rows.
- **What Parchment does with it**: `routers/tables.py`'s "try a sample page" button points at this URL; `etl/html_utils.py::fetch_and_parse_tables()` fetches and parses it live, exactly like it would any other user-provided URL.

## 4. Pretrained model weights (not "datasets," but also downloaded automatically)

| Model | Hub | Size (approx.) | Used for |
|---|---|---|---|
| Tesseract (LSTM OCR engine) | system package (`tesseract-ocr` + `tesseract-ocr-kor`) | ~15 MB (eng+kor traineddata) | Classic image-to-text |
| `HuggingFaceTB/SmolVLM-256M-Instruct` | HuggingFace | ~500 MB | Local vision-language model |
| `Qwen/Qwen2.5-0.5B-Instruct` | HuggingFace | ~2 GB (fp32) | OCR-text structuring, PDF/table insight |
| `sshleifer/distilbart-cnn-12-6` | HuggingFace | ~1.2 GB | PDF summarization |
| `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace | ~90 MB | Duplicate-detection embeddings |

All HuggingFace models are cached in the `parchment_hf_cache` Docker named volume after first download, so restarts never re-download them. Tesseract's traineddata files are baked into the image at build time (an apt package, not a runtime download).
