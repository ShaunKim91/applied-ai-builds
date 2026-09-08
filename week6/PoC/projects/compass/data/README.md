# data/

Unlike the Week4 "Lucent" PoC (which downloaded and indexed a fixed
document corpus at bootstrap), Compass has no static seed dataset — this
week's retrieval source is the live web, fetched fresh per query via
`ddgs` (with a mock fallback; see `backend/app/search/web_search.py`).

At runtime, this directory holds only what the running app itself
generates: the SQLite database (research sessions, reports, audit log,
budget setting) and the Chroma vector store (the archive index of past
reports). Both are created fresh on first boot and are gitignored.
