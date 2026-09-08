# Data sources

Both data sources below are downloaded automatically — you never need to do
this by hand. `backend/app/main.py`'s startup hook calls the same functions
shown here in a background thread on first boot; `scripts/download_data.sh`
is a manual trigger if you ever want to force a re-check.

## 1. Sample audio — Meeting Transcription demo clips

### 1a. `jfk.flac` (public domain)

- **Source**: `openai/whisper`'s own GitHub repository test asset
  <https://github.com/openai/whisper/blob/main/tests/jfk.flac>
- **Direct download**: <https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac>
- **License**: a recording of a U.S. presidential address. As a work of the U.S. federal government, it is in the public domain under U.S. copyright law (17 U.S.C. §105). It is also the exact demo file OpenAI ships inside the official Whisper repository and features in Whisper's own documentation/examples.
- **What VoxIQ does with it**: `backend/app/etl/audio_samples.py::ensure_sample_audio()` downloads it once to `data/sample_audio/`, offered as a one-click "try a sample" option on the Meeting Transcription page.

### 1b. LibriSpeech samples (CC BY 4.0)

- **Source**: `hf-internal-testing/librispeech_asr_dummy` on the HuggingFace Hub
  <https://huggingface.co/datasets/hf-internal-testing/librispeech_asr_dummy>
- **Underlying dataset**: LibriSpeech (Panayotov, V., Chen, G., Povey, D., Khudanpur, S. "Librispeech: An ASR corpus based on public domain audio books." *ICASSP 2015*), built from public-domain LibriVox audiobook recordings.
- **License**: CC BY 4.0 (Creative Commons Attribution 4.0 International)
- **Direct download**: the dataset's HF-auto-converted Parquet file, fetched directly (no `datasets` library dependency needed):
  `https://huggingface.co/api/datasets/hf-internal-testing/librispeech_asr_dummy/parquet/clean/validation/0.parquet` (9.19MB total, 73 clips; VoxIQ uses only the first 5)
- **What VoxIQ does with it**: `ensure_sample_audio()` downloads the parquet once, extracts the first 5 clips' embedded FLAC bytes, and writes them to `data/sample_audio/librispeech_{00..04}.flac`.

## 2. FOMC meeting minutes (public domain) — Knowledge Search corpus

- **Source**: Board of Governors of the Federal Reserve System
  <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>
- **URL pattern**: `https://www.federalreserve.gov/monetarypolicy/fomcminutes{YYYYMMDD}.htm`, where the date is the second day of each two-day FOMC meeting.
- **License**: official publications of a U.S. federal instrumentality — no copyright notice appears on these pages; they are published by the Federal Reserve for unrestricted public use, consistent with the public-domain treatment of U.S. federal government works generally.
- **Documents used** (7 real meetings, verified reachable before being hardcoded in `backend/app/etl/fomc_minutes.py`):
  | Date | Meeting |
  |---|---|
  | 2024-01-31 | Jan 30–31, 2024 |
  | 2024-03-20 | Mar 19–20, 2024 |
  | 2024-05-01 | Apr 30–May 1, 2024 |
  | 2024-06-12 | Jun 11–12, 2024 |
  | 2024-07-31 | Jul 30–31, 2024 |
  | 2024-09-18 | Sep 17–18, 2024 |
  | 2025-01-29 | Jan 28–29, 2025 |
- **What VoxIQ does with it**: `ensure_fomc_minutes()` downloads each HTML page once, strips navigation/script/style via BeautifulSoup, and saves the plain-text minutes to `data/fomc_minutes/`. `chunk_text()` then splits each ~9,000-word document into ~220-word passages with 40-word overlap (a standard overlap-chunking technique) before each chunk is embedded and indexed into the Chroma vector store — see `routers/search.py::index_fomc_minutes()`. If a date's URL ever 404s (meeting schedules can shift), the download step logs and skips it rather than failing the whole bootstrap.
- **Download it yourself** (outside the app, for inspection): `curl -o fomc_minutes.htm https://www.federalreserve.gov/monetarypolicy/fomcminutes20250129.htm`

## 3. Pretrained model weights (not "datasets," but also downloaded automatically)

| Model | Hub | Size (approx.) | Used for |
|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace | ~90 MB | Bi-encoder embeddings |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | HuggingFace | ~90 MB | Cross-encoder reranking |
| `openai-whisper` (`tiny`) | OpenAI (via `openai-whisper` PyPI package) | ~75 MB | Speech-to-text |
| `Qwen/Qwen2.5-0.5B-Instruct` | HuggingFace | ~2 GB (fp32) | Local code-generation agent |
| `gpt2` | HuggingFace | ~500 MB | Tokenizer & attention explorer |

All five are cached in the `voxiq_hf_cache` Docker named volume after first download, so restarts never re-download them.
