# Issue 01 — Korean Wikipedia fetch returns 403, and its failure silently killed English-corpus indexing too

**Found**: during Lucent's real container bootstrap (not synthetic/fabricated — this is the actual
`/api/health/ready` output and container log from this build run).

## Symptom

```json
{
  "bootstrap_complete": false,
  "bootstrap_step_errors": {
    "dataset:seed_corpus": "Client error '403 Forbidden' for url 'https://ko.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles=%EC%97%B0%EB%B0%A9%EC%A3%BC%EC%9D%98%EC%9E%90_%EB%85%BC%EC%A7%91'"
  },
  "models": { "embeddings": true, "reranker": true, "local_llm": false }
}
```

Container log:
```
[ERROR] lucent: Bootstrap step failed: dataset:seed_corpus (will retry lazily on first real request instead)
httpx.HTTPStatusError: Client error '403 Forbidden' for url 'https://ko.wikipedia.org/w/api.php?...'
```

## Root cause — two distinct real bugs, one symptom

**Bug A: missing User-Agent header.** Wikimedia's API rejects requests carrying a generic/default
client User-Agent (httpx's own default, `python-httpx/<version>`) with a flat 403 — this is documented,
intentional policy, not a transient outage: <https://meta.wikimedia.org/wiki/User-Agent_policy>.
`fetch_korean_wikipedia_article()` in `backend/app/etl/seed_corpus.py` called `httpx.get(...)` with no
headers at all.

**Bug B: no fault isolation between the two independent corpora.** `ensure_seed_texts_cached()`
downloads the English Federalist Papers first (this succeeded — the file was written to disk), then
calls `fetch_korean_wikipedia_article()` for the *separate* Korean corpus with no `try/except`. When
that call raised, the exception propagated out of `ensure_seed_texts_cached()` entirely, so
`index_seed_corpus()` (`backend/app/routers/documents.py`) never reached the code that indexes the
already-downloaded English essays either. One external API's policy rejection silently prevented
**all 85 English Federalist essays** from being indexed — not just the Korean document that actually
failed. This directly contradicts the isolation the code's own docstring promised ("treated as an
isolated, non-fatal bootstrap step like everything else").

## Fix

1. Added a descriptive `User-Agent` header (`Lucent-PoC-Week4/1.0 (educational vibe-coding project;
   no contact endpoint)`) to the Korean Wikipedia request, per Wikimedia's stated policy.
2. Wrapped the Korean fetch specifically in `try/except httpx.HTTPError` inside
   `ensure_seed_texts_cached()`, so a Korean-side failure now degrades to `korean_path: None` instead of
   aborting the whole function — the English corpus indexes regardless of whether the Korean fetch
   succeeds.

No user-identifying information (e.g. a real contact email) was put in the User-Agent string — this
project's API keys/contact info are file-referenced, never embedded in an outbound request to a
third-party service.

## Verification

- Restarted the bootstrap after rebuilding the image with the fix; confirmed via
  `docker logs lucent` and `/api/health/ready` that `dataset:seed_corpus` completes with no error and
  `essays_indexed: 85`, `korean_indexed: true`.
- Confirmed via `/api/documents` that both the 85 English `Document` rows and the Korean Wikipedia
  `Document` row exist.
- Re-ran `verify_e2e.py`'s Korean cross-lingual query step and confirmed it retrieves a real source
  (see `../history/v1.0.0.md` for the actual E2E run output).
