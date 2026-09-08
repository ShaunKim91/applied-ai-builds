# Issue 04 — Rebuilds kept re-downloading ~1GB of Python packages instead of hitting cache

## Symptom

The first build (`scripts/setup.sh`) took several minutes to download
torch/transformers/diffusers/chromadb/etc., which is expected on a first
build. After a small **backend-only** code change (three files touched, zero
dependency changes) a follow-up `docker compose build` was expected to reuse
the cached pip-install layer and finish in seconds. It didn't — it
re-downloaded everything (~5 minutes). A third rebuild, run with the exact
same command right after, **also** missed cache.

## Investigation (documented honestly, including the dead end)

**First hypothesis (tested, did NOT fix it):** the Dockerfile's
`ARG TORCH_INDEX` was only ever supplied via an ad hoc `--build-arg` CLI flag
in `scripts/setup.sh`, never declared in `docker-compose.yml` — different
invocation paths resolving a build-arg differently is a real, documented
BuildKit cache-key gotcha, so this looked promising. Fix applied: declared
`build.args.TORCH_INDEX` directly in `docker-compose.yml` and simplified
`setup.sh` to rely on it instead of an inline flag (this change is still in
the repo — it's correct hygiene either way, see the code diff). **Result:
the very next rebuild, using the identical command both times, still missed
cache against the immediately-prior build.** That result rules out the
build-arg theory as the (sole) cause here — two back-to-back, byte-identical
`docker compose build` invocations on this same machine still didn't share
cache with each other.

**More likely real cause**: `docker system df` showed this development
machine already had **~24GB of Docker build cache with ~20GB marked
reclaimable** *before* this project's first build even ran (from unrelated
prior Docker usage on the machine) — right at the range where Docker
Desktop's default build-cache GC threshold kicks in. A large, recently-created
layer (like a ~1GB pip-install layer) can be evicted by a GC pass shortly
after creation on a machine that's already near its cache budget, even
though it would otherwise be reused. This is a property of *this shared dev
machine's* pre-existing Docker usage, not of the project's Dockerfile.

## Fix applied / practical takeaway

The `docker-compose.yml` build-args declaration was kept (it's more correct
regardless, and removes one real source of non-determinism), but the actual
mitigation for this specific machine is operational, not code: run
`docker builder prune` (or free up Docker Desktop's cache budget) before a
sequence of rebuilds if iterating quickly. **This does not affect a student
following the README on a normal, non-cache-saturated machine** — a fresh
`git clone` + `./scripts/setup.sh` only ever pays the download cost once, the
same as originally documented; this issue only surfaced because of
back-to-back rebuild cycles during active development on an
already-cache-heavy machine.

## Verification

Confirmed functionally: both post-fix rebuilds produced a working,
healthy container each time (see `../history/v1.0.0.md`) — this issue only
ever affected **rebuild speed**, never correctness.

## What to study if this is new to you

- Docker layer caching is not an unlimited log — real CI/dev machines
  garbage-collect it under size pressure, and a "should have been cached"
  layer can still miss for reasons outside your Dockerfile entirely. Before
  concluding "my Dockerfile has a caching bug," check `docker system df` for
  cache pressure on the machine itself.
- This is a build-tooling lesson specific to this project, not a general one
  — other, simpler Dockerfiles in this series don't use build-args at all
  (they hardcode the CPU-wheel `pip install torch` command directly), so
  this pitfall is specific to this PoC's added GPU/CPU auto-detection
  feature.
