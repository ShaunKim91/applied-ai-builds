# Debug Log — CommerceIQ (PoC)

This folder records real issues hit while building and verifying this
project — root cause, fix, and (where relevant) which underlying concept
explains it — so it doubles as a troubleshooting reference for anyone
extending this PoC or repeating a similar build.

Each issue gets its own `issue-NN-short-slug.md` file. This README is the
index; it is updated as issues are found, not written speculatively.

| # | Title | Root cause category |
|---|---|---|
| [01](issue-01-chromadb-posthog-telemetry-error.md) | chromadb posthog telemetry error on every collection call | Upstream dependency version skew (chromadb ↔ posthog) — cosmetic, no functional impact |
| [02](issue-02-email-validator-rejects-local-tld.md) | Admin login fails: `.local` email rejected as "not deliverable" | Wrong validation tool for the job (deliverability-checking `EmailStr` used for a login-ID field) — **real bug, fixed** |
| [03](issue-03-cold-start-timeout-and-readiness-probe.md) | Feature timeouts on first boot were really "still downloading" | Test-design gap (no readiness probe) — added `/api/health/ready` + a wait step, **fixed** |
| [04](issue-04-docker-build-arg-cache-invalidation.md) | Rebuilds kept re-downloading ~1GB of packages instead of hitting cache | Likely Docker build-cache GC pressure on this shared dev machine (~24GB pre-existing cache) — rebuild speed only, never a correctness issue; compose.yml build-arg hygiene improved regardless |
| [05](issue-05-mape-blows-up-on-zero-revenue-days.md) | MAPE reported as 131,574.8% on a real forecast run | MAPE's textbook zero-actual-value weakness ($0-revenue Saturdays in the real data) — **real bug, fixed** (excluded from MAPE + added sMAPE) |
| [06](issue-06-bootstrap-steps-not-isolated.md) | One failed dataset download silently skipped warming all 4 AI models | Unrelated steps shared one try/except (found via a transient DNS blip during the final clean-rebuild test) — **real bug, fixed** (each of 6 startup steps now isolated) |
| [07](issue-07-run-sh-unnecessary-port-switch.md) | `run.sh` needlessly switched ports when the container was already running | Port-busy check couldn't distinguish "occupied by something else" from "occupied by my own already-correct container" — **real bug, fixed** (checks `docker compose ps` first) |
