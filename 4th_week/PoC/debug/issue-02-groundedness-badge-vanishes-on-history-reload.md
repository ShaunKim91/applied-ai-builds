# Issue 02 — Groundedness badge disappears the moment a chat session's history is reloaded

**Found**: while capturing product screenshots — reopening an existing chat session (clicking it in the
sidebar, or a page refresh) rendered the assistant's message with its citations but with the
"✓ Grounded" / "⚠ Partially grounded" badge silently missing, even though the same message showed the
badge correctly at the moment it first streamed in.

## Root cause

Two different code paths build the assistant `Message` the frontend renders, and they disagreed on
shape:

- **Live stream** (`chat.py`'s `send_message` → SSE `done` event): sends a nested
  `"groundedness": {"passed": ..., "content_check": {"score": ...}, "citation_check": {...}}` object —
  exactly what `frontend/src/pages/Chat.tsx`'s `Groundedness` interface and its badge-rendering JSX
  (`m.groundedness.passed`, `m.groundedness.content_check.score`) expect.
- **History reload** (`GET /api/chat/sessions/{id}/messages` → `chat.py`'s `_message_dict()`): returned
  two *flat* keys instead, `groundedness_score` and `groundedness_passed`. The frontend's `Message` type
  never declared those keys, and `api.get<Message[]>(...)` performs no runtime shape validation — so
  `m.groundedness` was silently `undefined` for every reloaded message, and the badge's
  `{m.groundedness && (...)}` guard just skipped rendering. No error, no console warning — the feature
  quietly only ever worked for the single browser session in which a message was first sent.

## Fix

Changed `_message_dict()` in `backend/app/routers/chat.py` to build the same nested shape the SSE event
uses: `{"passed": m.groundedness_passed, "content_check": {"score": m.groundedness_score}}` for assistant
messages (`None` for user messages). `citation_check` detail isn't persisted per-message in the DB, so
it's omitted on reload — confirmed via a grep of the frontend's badge-rendering code that only `.passed`
and `.content_check.score` are actually read there, so this is a complete fix for the visible bug, not a
partial one.

## Verification

- Rebuilt the image, restarted the container, re-ran `verify_e2e.py` (13/13 still pass — it doesn't
  reload history, so it couldn't have caught this on its own; noted below).
- Manually: sent a message, confirmed the badge renders live; navigated away to Documents and back to
  Chat, reopened the same session, confirmed the badge **still renders** with the correct grounded/score
  values read back from the database.
- **Process note**: this bug shipped past `verify_e2e.py`'s 13 checks because none of them re-fetch a
  session's message history after the fact — they only ever check the live SSE response. Added to
  `history/checklist.md` as a known gap in this round's automated coverage (caught instead by manual
  screenshot-driven testing, which is exactly the kind of real-usage path automated checks were missing).
