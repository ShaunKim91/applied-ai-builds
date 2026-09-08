# Data sources

Both seed corpora below are prepared automatically — you never need to do
this by hand. `backend/app/main.py`'s startup hook calls the same functions
shown here in a background thread on first boot; `scripts/download_data.sh`
is a manual trigger if you ever want to force a re-check.

## 1. The Federalist Papers (English) — primary knowledge-base corpus

- **Source**: Project Gutenberg, eBook #18
  <https://www.gutenberg.org/ebooks/18>
- **Direct download** (verified reachable and correct before being hardcoded): <https://www.gutenberg.org/cache/epub/18/pg18.txt> (1.2 MB, HTTP 200 confirmed live)
- **License**: a work of the U.S. founding era (1787–1788) — public domain. Project Gutenberg's own eBook license permits free reuse; this project reads the plain-text file directly rather than redistributing it.
- **What Lucent does with it**: `etl/seed_corpus.py::parse_federalist_essays()` splits the full text on its `No. <roman-numeral>.` essay headings — real structural parsing, not a hand-maintained list — producing 85 real essays (verified count), each chunked (500 words / 50-word overlap) and embedded as its own `Document` row, so citations read as "Federalist No. 51" rather than an anonymous chunk index.

## 2. 연방주의자 논집 (Korean Wikipedia) — cross-lingual corpus

- **Source**: Korean Wikipedia, article "연방주의자 논집"
  <https://ko.wikipedia.org/wiki/연방주의자_논집>
- **Direct fetch**: the MediaWiki API's plaintext extract endpoint (`action=query&prop=extracts&explaintext=1`), not a scrape of the rendered HTML — see `etl/seed_corpus.py::fetch_korean_wikipedia_article()`.
- **License**: CC BY-SA 4.0 (Wikipedia contributors) — fetched live and indexed on demand, credited here per the license's attribution requirement.
- **Why this specific article**: it's directly on-topic with the English corpus (both are about the same historical work), which is exactly what makes the multilingual embedding model's cross-lingual retrieval claim something a real question can demonstrate rather than just assert — see `history/v1.0.0.md` for the actual Korean-language query tested against this build.

## 3. User uploads

Any `.txt`, `.md`, or `.pdf` file a signed-in user uploads via the Documents page is chunked and indexed the same way as the seed corpora (`routers/documents.py::upload_document`). Uploaded files are stored under the `lucent_data` Docker volume and are never sent to any third party — indexing is 100% local (the embedding model), and the file only leaves the container if a user later opts in to the OpenRouter chat provider, in which case only the retrieved chunk text (not the raw file) is sent as part of the prompt.

## 4. Pretrained model weights (not "datasets," but also downloaded automatically)

| Model | Hub | Size (approx.) | Used for |
|---|---|---|---|
| `intfloat/multilingual-e5-small` | HuggingFace | ~470 MB | Bi-encoder embeddings (retrieval + groundedness check) |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | HuggingFace | ~90 MB | Cross-encoder reranking (opt-in) |
| `Qwen/Qwen2.5-0.5B-Instruct` | HuggingFace | ~2 GB (fp32) | Streaming local answer generation |

All three are cached in the `lucent_hf_cache` Docker named volume after first download, so restarts never re-download them.
