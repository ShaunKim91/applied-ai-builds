# Issue 07 — `run.sh` needlessly switched ports when the container was already running

## Symptom

After a Docker Desktop restart, its `restart: unless-stopped` policy brought
the `commerceiq` container back up on its stored port (8720) automatically.
Running `./scripts/run.sh` right after that printed:

```
Port 8720 is currently occupied by something else — picking a new one.
CommerceIQ: http://localhost:8721
```

...and actually recreated the container on a new port, even though the
*correct*, already-running instance was sitting right there on 8720.

## Root cause

`run.sh`'s `is_port_free()` check can't distinguish "occupied by something
unrelated" from "occupied by this exact container, correctly, already." When
the container had already auto-restarted before the script ran, the stored
port was — accurately — no longer free, so the script's only fallback path
(pick a new port) fired even though nothing was actually wrong.

## Fix applied

`run.sh` now checks `docker compose ps --status running --services` for the
`app` service *first*. If it's already running, the script reports the
existing URL and exits immediately — the port-conflict-resolution logic only
runs when the container genuinely isn't up yet. (`setup.sh` was left
as-is: it always does a full build+up cycle by design, so an occasional
redundant recreate there is expected behavior, not a bug — the issue was
specific to `run.sh`'s documented "fast, resume-only" role.)

## Verification

Re-ran `./scripts/run.sh` with the container already healthy on 8721 (a
port it had legitimately moved to earlier) — it now correctly reports
`CommerceIQ is already running: http://localhost:8721` and does nothing
else, with no container recreation and no port change.

## What to study if this is new to you

- **A "port busy" check has (at least) two different causes, and they need
  different responses**: busy-by-something-else (genuinely need a new port)
  vs. busy-by-my-own-already-correct-process (do nothing). Treating both
  cases identically — as this script initially did — produces "fixes" for a
  problem that was never actually there.
- This was found by a human reviewer actually running the script against a
  live system after a real Docker Desktop restart, not by reading the code
  — a good reminder that idempotency scripts (`run.sh`'s whole premise) are
  worth exercising against the specific edge case they claim to handle
  ("already running") rather than only against the cold-start case.
