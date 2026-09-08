# data/

Docker-volume-mounted persistent storage (`throughline_data`):

- `app.db` — SQLite, the system of record (organizations, users, cases,
  conversation turns, memory facts, audit log, etc.)
- `chroma/` — Chroma's persistent vector store (case summaries, for the
  Workspace directory's semantic search)

Nothing in this directory is committed to version control (see
`.gitignore`) — it is real runtime data, populated the first time the
container starts, and preserved across `docker compose stop`/`up` cycles.
