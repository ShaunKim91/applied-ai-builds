# Debug Log — VoxIQ (Week2 PoC)

This folder records real issues hit while building and verifying this
project — root cause, fix, and (where relevant) what underlying concept
it touches — so it doubles as a troubleshooting
reference for anyone extending this PoC or repeating a similar build.

Each issue gets its own `issue-NN-short-slug.md` file. This README is the
index; it is updated as issues are found, not written speculatively.

Compared to the Week1 PoC ("CommerceIQ"), this build hit far fewer issues
— by design: VoxIQ's scaffolding deliberately reused CommerceIQ's
already-debugged `security.py`, auth router, `_warm_step()` bootstrap
isolation, readiness-probe endpoint, and `run.sh` idempotency check from
day one (see `../architecture.md` §5), so the classes of bug Week1 needed
a follow-up pass to find never had a chance to reappear here. The first-ever
`verify_e2e.sh` run against VoxIQ passed 12/12 with zero real bugs.

| # | Title | Root cause category |
|---|---|---|
| [01](issue-01-setup-sh-stale-model-count.md) | `setup.sh` printed "4 local AI models" (VoxIQ has 5) | Leftover literal from copy-adapting CommerceIQ's script — cosmetic only, **fixed** |
| [02](issue-02-local-llm-misreads-dict-shape.md) | Analytics Agent's local model (Qwen2.5-0.5B) reliably generated code that crashed with `ValueError: too many values to unpack` | Small-model prompt-following gap — the system prompt described the data shape but not how to iterate it; the 8B OpenRouter model didn't make the same mistake — **real bug, fixed** (explicit anti-example + correct-usage example added to the prompt) |

## How these were found

Both issues were found by actually using the running app, not by reading
code: issue-01 by comparing `setup.sh`'s own printed output against
`README.md` and `download_models.sh` during a routine consistency check;
issue-02 by reading a Playwright screenshot taken for documentation
purposes and noticing a visible Python stack trace in the "Sandbox output"
panel, then reproducing it deterministically via direct `curl` calls before
fixing and re-verifying.
