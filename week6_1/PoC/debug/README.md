# Debug Log — Throughline (Week6_1 PoC)

Real issues only, found via actual manual testing (local FastAPI `TestClient` runs against the real
local model during development, followed by the full `verify_e2e.py` suite against the real Docker
container) and direct traceback inspection — never fabricated. Each entry links a symptom actually
observed to a root cause actually confirmed in the code.

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-detached-orm-instance-across-sse-session-boundary.md) | A `MemoryConflictLog` row created in one `SessionLocal()` session was read again after that session closed, crashing the second half of any turn that produced a memory conflict | High | Fixed, regression-tested |
| [02](issue-02-memory-facts-never-reached-the-reply-prompt.md) | Structured `MemoryFact` rows were extracted, persisted, and shown in the UI sidebar, but never actually injected into the reply-generation prompt — the memory feature didn't functionally do anything beyond decorate a sidebar | High | Fixed, regression-tested |
| [03](issue-03-chatpromptvalue-not-subscriptable-in-summarization.md) | Piping a real `ChatPromptTemplate` directly into the shared local-model `Runnable` handed it a `ChatPromptValue`, not a message list — crashed the window-to-summary transition the first time it actually ran | High | Fixed, regression-tested |
| [04](issue-04-callback-window-preference-never-matched-fixed-slots.md) | A caller's "morning"/"afternoon" preference correctly auto-filled into a tool call, but the tool's own literal-substring match against `"...AM"`/`"...PM"`-stamped slots never actually fired | Low | Fixed, covered by E2E |

## Why four real bugs this round, not zero

Verity found three new bugs of its own; Threshold carried forward every one of the predecessor
Cradle PoC's own bug classes correctly from the start and found one new one (in two manifestations)
specific to its own richer tool-argument surface. Throughline's own genuinely new surface area —
real multi-session-boundary SQLAlchemy usage across an SSE generator, a second independent LCEL
composition shape (`ChatPromptTemplate | Runnable`, not just a hand-built message list), and
structured memory that has to actually reach the model, not just get persisted — gave rise to its own
new failure modes, none of which either sibling product's own testing had reason to exercise. All
four were found through direct, deliberate multi-turn conversation testing (first against a local
`TestClient` process for fast iteration, confirmed again in the real Docker container), not by
`verify_e2e.py` alone — the suite's own relevant regression steps were written *after* each fix, to
lock it in, following this project's standing practice throughout the whole Fenwick Mutual suite.

## A real finding that is not a product bug

While iterating locally (outside Docker, directly against a Python virtual environment on this
development machine) to get fast feedback before committing to a full container rebuild, one test run
produced `RuntimeError: unsupported scalarType` and a "model on `meta` device" warning from
`transformers`, and a separate run crashed at Python process exit with
`libc++abi: ... recursive_mutex lock failed`. Both traced to this local macOS development environment
specifically: the local probe virtual environment installed the default (non-CPU-restricted) `torch`
build, which auto-detected Apple Silicon's `mps` backend (visible in that run's own log line, `Use
pytorch device_name: mps`) — a device this app's code never explicitly requests and the real Docker
deployment (Linux, the CPU-only `torch==2.8.0+cpu` wheel pinned in `docker/Dockerfile`) never has
available at all. Confirmed as an artifact of that mixed CPU/MPS local environment, not a product
defect, by the real Docker container: the same class of multi-turn, model-loading, and background-
thread activity ran cleanly across three full clean rebuilds with zero occurrences of either symptom,
and every `verify_e2e.py` run against the container passed without incident.
