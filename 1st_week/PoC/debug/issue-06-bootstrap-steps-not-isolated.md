# Issue 06 — One failed dataset download silently skipped warming all 4 AI models

## Symptom

During the project's final clean-reproducibility check (`docker compose down
-v` + `docker rmi` + a completely fresh `scripts/setup.sh` run — no prior
image, no prior volumes), `GET /api/health/ready` reported:

```json
{
  "bootstrap_complete": true,
  "bootstrap_error": "HTTPSConnectionPool(host='archive.ics.uci.edu', port=443): Max retries exceeded ... Failed to resolve 'archive.ics.uci.edu' ([Errno -5] No address associated with hostname)",
  "models": {"vision": false, "diffusion": false, "embeddings": false, "local_llm": false},
  "all_warm": false
}
```

**None** of the 4 AI models had loaded — not just the dataset download that
actually failed.

## Investigation

Checked DNS resolution inside the container immediately after:

```
$ docker compose exec -T app sh -c "getent hosts archive.ics.uci.edu"
128.195.10.252  datalab-12.ics.uci.edu archive.ics.uci.edu
```

It resolved fine, moments later. This was a **transient DNS hiccup** — a
known Docker Desktop behavior where the embedded resolver (`127.0.0.11`)
can briefly fail to forward queries right after a *brand new* Docker network
is created (which `docker compose down -v` followed by `up` does), before
upstream DNS forwarding stabilizes. Real infrastructure flakiness, not a
project bug in itself.

## Root cause (the part that *was* a real bug)

`main.py`'s `_warm_cache()` wrapped its **entire** body — both dataset
downloads AND all 4 model loads — in a single `try/except`. The UCI dataset
download is the *first* thing it does; when that raised, the `except` caught
it and the function returned immediately, having never reached the model
loading code at all. A one-off DNS blip fetching a dataset that has *nothing
to do with* the AI models took all 4 of them down with it, purely because
of unrelated code sharing one try/except block.

## Fix applied

Refactored into `_warm_step(name, fn)` — each of the 6 startup operations
(2 dataset downloads + 4 model loads) now runs in its own isolated
try/except and is attempted regardless of whether an earlier step failed.
`state.bootstrap_step_errors` (a dict, replacing the old single
`bootstrap_error` string) records failures per-step, so `/api/health/ready`
can show precisely which step(s) failed without hiding the ones that
succeeded. Both dataset-download functions were already idempotent/safe to
retry (`ensure_online_retail_daily`/`ensure_sample_images` check what's
already on disk and only fetch what's missing), so a failed step here
self-heals the next time a real request actually needs that dataset —
no manual intervention required.

## Verification

Rebuilt with the fix (`docker compose build && docker compose up -d`, reusing
the same volumes the DNS failure above had left partially populated) and
let bootstrap run again. This time the dataset download simply succeeded
(the DNS hiccup didn't recur) — so this pass didn't re-exercise the isolation
logic against a live failure, only confirmed `bootstrap_step_errors` stayed
empty and all 4 models + both datasets warmed correctly (`GET
/api/health/ready` reached `"all_warm": true`), followed by a clean 12-step
`verify_e2e.sh` pass. **Being precise about what was and wasn't proven**: the
isolation itself (each step in its own try/except, verified by reading the
code — `_warm_step()` in `main.py`) is straightforward enough to trust by
inspection, but a second *live* DNS failure to confirm the fix under the
exact original conditions was not observed in this build. If you want to
verify it directly yourself: temporarily point `SOURCE_URL` in
`etl/online_retail.py` at an unreachable host and confirm the other 3
models/dataset still warm normally. See `../history/v1.0.0.md`'s
Reproducibility section for the full clean-rebuild account.

## What to study if this is new to you

- **Don't let unrelated operations share a failure boundary.** A single
  `try/except` around N independent steps means step 1's failure silently
  cancels steps 2..N even when they have no dependency on step 1 — a subtle
  but common source of "why didn't X even try to run?" bugs. The fix is
  almost always to give each independent unit of work its own try/except
  (or use a structured concurrency / task-group pattern that reports
  per-task outcomes).
- **Idempotent, resumable I/O is what makes "fail now, retry later" safe.**
  This fix only works cleanly because the dataset-download functions were
  already written to check what's already on disk before fetching — the
  general principle (make network/download steps safely re-callable) is
  what turns a transient failure into a non-event instead of a corrupted
  half-downloaded state.
- Related principle: this is the same "각 도구는 독립적으로 실패해야 한다"
  (each tool/step must fail independently) principle behind this project
  series' own hybrid-CLI augmentation pattern used elsewhere — independent
  augmentation paths are deliberately wrapped in *separate* try/excepts so
  one failing never blocks the other or the local default. This bootstrap
  fix applies the identical idea to dataset vs. model warm-up.
