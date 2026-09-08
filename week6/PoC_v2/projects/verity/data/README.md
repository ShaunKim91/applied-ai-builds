# data/

Empty in the repository — populated at runtime inside the Docker volume `verity_data`:

- `app.db` — SQLite database (organizations, users, refresh tokens, research sessions/entries, CAT events, budget settings, hash-chained audit log, error log)
- `chroma/` — Chroma `PersistentClient` vector store (past-report embeddings for the Claim Research Library's semantic search)

Verity has no static seed corpus this round — its claims/jurisdiction research is grounded in a fully fictional, code-defined corpus (`backend/app/search/jurisdictions.py`), not an indexed document set. See that file's module docstring for why.
