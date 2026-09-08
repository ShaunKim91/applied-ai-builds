# data/

Cradle has no static seed dataset — there's nothing to pre-index, since the
product is a local tool-using agent, not a document or search pipeline.

At runtime, this directory holds only what the running app itself
generates: the SQLite database (agent runs, steps, approval requests,
guardrail/budget settings, audit log) and the Chroma vector store (the
History page's semantic index over past agent runs). Both are created
fresh on first boot and are gitignored.
