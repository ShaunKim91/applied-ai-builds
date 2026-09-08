# Issue 01 — PDF summarization timed out (and read poorly) on a real long document

## Symptom

The very first real `verify_e2e.sh` run against Parchment failed on exactly
one step:

```
[FAIL] pdfs: summarize sample (numeric cross-check) (180.0s) — HTTPConnectionPool(host='localhost', port=8000): Read timed out. (read timeout=180)
```

The other 12 checks passed. This was against the real bundled sample — the
Federal Reserve's actual Monetary Policy Report PDF, not a toy document.

## Root cause

The Fed report is a genuinely long document: **34,267 words**, which
`chunk_text()`'s original 220-word chunking produced as **191 chunks**.
`summarize_long_text()`'s map-reduce implementation summarized each chunk
one at a time in a plain Python loop (`[_summarize_one(c) for c in
chunks]`) — 191 sequential calls into `distilbart-cnn-12-6` on CPU, each
paying its own tokenization + generation overhead. This comfortably
exceeded the 180-second HTTP timeout the E2E script (reasonably) used.

A second, related problem surfaced once the first was partially fixed: even
after switching to **batched** inference (`pipe(chunks, batch_size=8, ...)`
instead of one call per chunk), a first fix landed at 60 sampled chunks and
measured **166.7 seconds** — technically under the timeout, but by an
uncomfortably thin margin, and the resulting summary itself read like a
table of contents ("Part 2: Monetary Policy . Part 3: Summary of Economic
Projections . Part 4: ...") rather than substantive content — a symptom of
combining too many very short (~15-20 word), mutually disconnected partial
summaries in the "reduce" step.

## Fix applied

Three changes together, in `backend/app/ml/summarizer.py` and `config.py`:

1. **Batched inference**: `_summarize_batch()` calls the pipeline once with
   a list of chunks (`batch_size=8`) instead of once per chunk, letting the
   model's forward pass actually parallelize across chunks (confirmed via
   `docker stats` showing ~960% CPU during the batched run, vs. much lower
   utilization in the original sequential loop).
2. **Larger chunks, tighter cap**: `pdf_chunk_size_words` raised from 220 to
   500 words, and a new `MAX_CHUNKS = 20` hard cap — chunks beyond the cap
   are evenly sampled across the document's full span (not just the
   opening section) rather than processing all of them. This is reported
   back to the caller as `chunk_count` (total) vs. `chunks_summarized`
   (actually used) — surfaced in the UI as an explicit, non-silent notice
   when truncation happens (`pdfs.chunksTruncated` in the i18n files),
   rather than silently pretending the summary covered everything.
3. **`truncation=True`** on every pipeline call — a defensive fix caught
   during code review (not itself the cause of the timeout), since BART's
   fixed 1024-token position-embedding limit would otherwise raise an
   `IndexError` on the "reduce" step's combined-text input for a
   sufficiently long document, which has no guaranteed length.

## Verification

Measured directly (`curl` + `time`) against the real Fed report PDF before
and after each change:

| Version | Chunks (total → summarized) | Latency | Summary quality |
|---|---|---|---|
| Original (sequential, 220-word chunks) | 191 → 191 | **timed out at 180s** | n/a |
| Batched, 60-chunk cap | 101 → 60 | 166.7s | poor — table-of-contents-like |
| Batched, 500-word chunks, 20-chunk cap | 78 → 20 | **56.7s** | good — coherent, states the actual policy rate (5¼–5½ percent) and FOMC context, all numbers verified against source |

Re-ran the full `verify_e2e.sh` suite after the final fix: **13/13 passed**,
including the PDF step at 56.7s — comfortably under the 180s timeout with
real margin, not just barely inside it.

## What to study if this is new to you

- **A number that "passes" isn't the same as a number with margin.** The
  intermediate 166.7s fix technically avoided the timeout in this one test
  run, but was one slow moment (a busier host, a longer document) away from
  failing again — the goal was headroom, not a bare pass.
- **Batching alone doesn't fix a scaling problem — it just raises the
  ceiling.** The real fix was reducing how much text actually needs a full
  generation pass (larger chunks, an explicit cap, even sampling), not only
  making each pass faster.
- **A performance fix and a quality fix were the same fix here.** Feeding
  the "reduce" step 20 substantive, well-covered partial summaries instead
  of 60-191 tiny fragmentary ones produced both a faster *and* a more
  coherent final summary — worth noticing when a slow path and a
  low-quality path share one root cause.
- **Surface truncation, don't hide it.** Once a cap on how much of a
  document actually gets summarized exists, the honest move is telling the
  user exactly what happened (`chunk_count` vs. `chunks_summarized`, shown
  in the UI), not silently returning a summary that quietly only reflects
  part of the source.
