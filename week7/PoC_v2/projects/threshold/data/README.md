# data/

Empty in the repository — populated at runtime inside the Docker volume `threshold_data`:

- `app.db` — SQLite database (organizations, users, refresh tokens, agent runs/steps, approval requests, guardrail/budget settings, hash-chained audit log, error log)
- `chroma/` — Chroma `PersistentClient` vector store (past-run embeddings for History's semantic search)

Threshold has no static seed corpus this round — its only "world" is a small, fixed set of local Python tool functions (claims lookups, payout math, currency conversion, procedure lookups), none of which need pre-indexing.
