# Issue 01 — A newly-created research thread's entries could theoretically be silently wiped by a stale background fetch

**Found**: while investigating a screenshot showing "No research yet in this thread" immediately
after a genuinely successful (200 OK) research query, reading through `Research.tsx`'s state
management for a plausible cause of a stale/overwritten `entries` array.

## Root cause

`startNewThread()` created a new session and called `setActiveId(session.id)`. A separate
`useEffect(() => { if (activeId) loadEntries(activeId); ... }, [activeId])` reacted to that change
by firing a fresh `GET /api/research/sessions/{id}/entries` — a trivial, normally-instant DB lookup.
Immediately afterward, `submit()` started streaming the actual research query, whose local LLM
generation can take several (quick mode) to 20+ (precedent-brief mode) seconds. Python's GIL means
the blocking `model.generate()` call running in one thread can meaningfully delay a concurrent
lightweight request being scheduled/processed on another thread. If that delayed `GET .../entries`
call happened to resolve **after** the streaming query's own `done` handler had already appended the
real entry to state, its stale (correctly-empty-at-the-time-it-was-issued) response would
unconditionally overwrite `entries`, making a genuinely completed answer disappear from the screen.

This specific screenshot failure turned out to have a different, more mundane immediate cause (see
the non-bug findings in `README.md` — a Playwright wait-condition mistake), so this exact race did
not in fact fire in that instance. But the underlying architectural risk is real and independently
reproducible in principle: any code path that re-fetches and unconditionally replaces `entries` in
response to `activeId` changing, while a query for that same session is concurrently streaming, is
vulnerable to this ordering.

## Fix

Removed the `useEffect([activeId])` entirely. Entries are now loaded only in direct response to an
explicit user action:
- Opening an existing thread from the sidebar (`openSession()`) — the only place a background fetch
  of entries is still needed.
- Creating a brand-new thread (`startNewThread()`) — sets `entries` to `[]` directly and
  synchronously, since a session that was just created cannot have any entries yet; no network
  round-trip needed for an answer already known.

This eliminates the race by eliminating the redundant, implicitly-triggered fetch altogether, rather
than trying to out-time it.

## Verification

- Re-ran the full research flow (create thread → quick query → precedent-brief query in the same
  thread) on a clean rebuild; both entries render and persist correctly with no disappearing state.
- Re-ran `verify_e2e.py`'s `step_research_quick` and `step_precedent_brief` (16/16 overall still
  pass) — these don't specifically stress this race's timing window, so they wouldn't have caught it
  either way; the fix is a structural one, not something an added timing-dependent test would
  reliably re-catch.
