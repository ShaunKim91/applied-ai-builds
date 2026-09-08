# Issue 03 — Feature timeouts on first boot were really "still downloading," not a bug

## Symptom

Real output from the first live end-to-end verification run:

```
[FAIL] generate: submit + poll a diffusion job (tiny-sd) (421.1s) — generation job did not finish in time
[FAIL] forecast: Holt-Winters + AI insight (local Qwen2.5-0.5B) (300.1s) — Read timed out. (read timeout=300)
```

## Investigation

Checked whether the diffusion job actually finished anyway, just after the
script gave up waiting:

```
$ docker compose exec -T app sh -c "ls -la /app/data/generated/"
-rw-r--r-- 1 root root 333948 Aug 23 21:06 45a011403187440495083b682acd443e.png
```

It had. Checked whether the local-LLM download was still genuinely in
progress (not hung):

```
$ docker compose exec -T app sh -c "du -sh /app/hf_cache/.../blobs/*.incomplete"
245M	.../fdf756fa....incomplete
```

A `.incomplete` file that's still growing over repeated checks confirms this
was a real, actively-progressing download on an unusually slow connection in
this build environment (observed ~0.6–1.5 MB/s) — not a hang, deadlock, or
application bug. `Qwen2.5-0.5B-Instruct` (~2GB fp32) simply hadn't finished
downloading by the time the forecast step's 5-minute HTTP timeout elapsed,
and the background bootstrap thread (loading models sequentially) and the
job thread (loading tiny-sd for the generate request) were both competing
for the same limited bandwidth at once.

## Root cause

Not a functional bug — a **test-design gap**: the E2E script's per-step
timeouts conflated two different things: "is this AI feature's *own* logic
correct" and "has this model finished its one-time download yet." On a slow
network, the second can legitimately take longer than any reasonable
per-feature timeout budget.

## Fix applied

1. Added a real **readiness signal**, `GET /api/health/ready` (no auth
   needed), that reports each of the 4 local models' actual loaded state —
   reusing the same technique `routers/admin.py` already used for its
   authenticated system-status view, so there's one source of truth, not a
   second hand-maintained flag that could drift from reality.
2. Added `step_wait_for_warm()` as the **first** real step in
   `verify_e2e.py`, polling that endpoint (up to 20 minutes) before running
   any feature test. This decouples "wait for the one-time download" from
   "test the feature," which is the same separation container orchestrators
   use (a liveness probe vs. a readiness probe) — `/api/health` (liveness,
   always instant) is unchanged and still what Docker's `HEALTHCHECK` uses.
3. Raised the per-feature timeouts as defense-in-depth (generate: 7→10 min,
   forecast: 5→10 min) in case a model is re-triggered to reload mid-test for
   any reason, even though `step_wait_for_warm` should make these rarely
   matter in practice.

## Verification

Re-ran `scripts/verify_e2e.sh` after the fix — see `../history/v1.0.0.md`
for the timing of the readiness-wait step and the (now fast, warm-cache)
feature steps that followed it.

## What to study if this is new to you

- **Liveness vs. readiness** is a standard container-orchestration concept
  (Kubernetes calls them exactly that): liveness = "is the process alive at
  all," readiness = "is it ready to serve *this specific kind of* traffic
  well." Conflating them is a common mistake in hand-rolled health checks.
- Related principle: this is the same "느린 최초 다운로드는 정상, 감점 아님"
  (slow first-time download is expected, don't penalize) idea that verification
  checklists for this kind of project commonly call out — here it's solved
  with real code (a readiness endpoint) instead of just a note telling a
  human reviewer not to worry about it.
