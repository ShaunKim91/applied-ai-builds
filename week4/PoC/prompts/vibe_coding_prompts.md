# Vibe-Coding Prompt Playbook — Lucent (Week4 PoC)

This is the prompt sequence a student could actually use — with an AI coding
tool such as Claude Code — to reproduce a project like Lucent from scratch.
It mirrors the Week1-3 PoCs' own playbooks in structure, with new phases
this round for streaming and for turning a vague "make it more advanced/
transparent/valuable" request into something buildable and checkable.

## Phase 0 — Research before touching code

> Research the relevant background (RAG fundamentals, embeddings/cosine
> similarity, VectorDB/Chroma, chunking + citation-based answers) and a
> typical reference implementation's exact library/model/chunking choices —
> including checking whether any written documentation's own code samples
> still match what the actual shipped code does.

**Why the second half matters**: this specifically caught that a piece of
reference documentation's own quoted code (a hash-based mock embedding)
didn't match what the actual reference implementation shipped (a genuine
`sentence-transformers` model) — the underlying code had been updated once
but the accompanying documentation wasn't fully revised to match. Building
against the stale documented sample instead of the actual shipped model
would have been a real, avoidable mistake.

## Phase 1 — Turn a qualitative request into a concrete, checkable plan

> The brief this round is "more advanced, a more transparent/polished UI,
> and much higher product value than the last three builds." Before writing
> any code, turn each of those three asks into something specific: (a) name
> the exact features that make this "more advanced" than a typical baseline
> implementation — table it, dimension by dimension; (b) name the exact visual
> tokens (font, color, navigation shape) that make the UI different and
> justify why "glass/transparency" fits this week's RAG-grounding theme
> semantically, not just visually; (c) name the exact product feature that
> represents "higher value" (e.g., real streaming, not just a nicer UI skin
> on the same request/response pattern).

**Why**: "make it better" is unverifiable prose. A dimension-by-dimension
comparison table (this build's `architecture.md` §2) is something you can
actually check was delivered once the build is done — and it's what let
this specific plan commit to concrete, buildable items (streaming,
groundedness checking, a real bilingual corpus) instead of vague polish.

## Phase 2 — Verify facts with live tools, not memory

> Before finalizing the seed corpus: confirm the exact direct-download URL
> for a real public-domain English text resolves and is the right content;
> confirm a Korean-language source on a directly related topic actually
> exists (search for it by its real title, don't guess a URL); if you're
> parsing a document into structural units (e.g., splitting 85 essays by
> their headings), test the parsing regex against the real downloaded text
> and sanity-check the resulting count before committing to a design.

**Why the last point specifically**: a first attempt at the Federalist
Papers' essay-heading regex produced 86 matches instead of the expected 85
— caught by actually counting, not assumed. The fix wasn't to hand-tune the
regex around one anomaly; it was to defensively filter out any resulting
essay body under a minimum length, which handles that (and similar) edge
cases without needing to fully diagnose the one stray match.

## Phase 3 — Scaffold, reusing infrastructure files verbatim where safe

> Copy every backend file with no project-specific business logic
> (`security.py`, `database.py`, `state.py`, `audit.py`, `media.py`, the
> auth router, `vectorstore.py`, `reranker.py`) from the most recent prior
> project. Write new modules only for what's genuinely new this week
> (`embeddings.py` with the E5 query/passage prefix convention, streaming
> support in `llm.py`, `groundedness.py`, the seed-corpus ETL).

## Phase 4 — Backend: build streaming as a first-class citizen, not a retrofit

> Implement the streaming chat endpoint from the start as a
> `StreamingResponse` yielding SSE-shaped lines, with the local provider
> using `TextIteratorStreamer` on a background thread and the cloud
> provider parsing real `stream: true` SSE events — not a non-streaming
> `generate()` call with the response chunked artificially after the fact.
> Remember that a DB session opened via a FastAPI dependency will likely be
> closed before a streaming generator body actually finishes running — open
> a fresh session inside the generator for any writes that happen after
> streaming completes.

**Why the DB session note matters**: this is a real, easy-to-miss FastAPI +
`StreamingResponse` gotcha — the dependency-injected session's lifecycle is
tied to the route handler function returning, not to the response body
being fully sent to the client, which happens later.

## Phase 5 — Frontend: design tokens first, then a real streaming consumer

> Before any page component, write the new design tokens (a gradient mesh
> background, translucent glass card class, one weight-driven font family,
> a floating sidebar shape). Then build the chat UI to consume the stream
> via `fetch()` + a `ReadableStream` reader (a plain GET-only `EventSource`
> cannot carry the POST body a chat message needs) — parse the SSE framing
> by hand, append each fragment to the growing message in state as it
> arrives, so the UI visibly streams rather than waiting for the final
> event before rendering anything.

## Phase 6 — Containerize

> Same multi-stage Dockerfile pattern as before — this week needs no new
> system packages (no OCR/PDF-rasterization dependency this time), so keep
> the apt-get install minimal rather than carrying over a prior week's
> now-unneeded system packages by copy-paste habit.

## Phase 7 — Prove it actually works, including the streaming and cross-lingual claims specifically

> Write `verify_e2e.py` to actually consume the streaming response the same
> way a real client would (assemble the SSE fragments into a full answer,
> don't just check the endpoint returns 200), and include a genuine
> functional test of the multilingual retrieval claim — a real
> Korean-language question that must retrieve at least one real source, not
> just an English-language test that never actually exercises the
> cross-lingual embedding space.

## Phase 8 — Document with facts already in hand, not invented ones

> Write architecture.md, flowchart.md, and docs/guide.html using only facts
> already established — the real verify_e2e.sh output, the real dataset
> parsing counts (85 essays, verified), the specific
> more-advanced-than-baseline comparison table from Phase 1. Label any
> estimate (e.g. production cost) explicitly as one.

## General prompting habits used throughout this build

- **Convert a vague quality bar ("more advanced," "more valuable") into a
  table you can check against**, before writing any code — this is the
  single highest-leverage habit for a request phrased as an aspiration
  rather than a specification.
- **Verify structural parsing against real data, not just syntax** — a
  regex that compiles is not the same as a regex that produces the right
  count on the actual document it will run against.
- **Name the exact FastAPI + streaming gotcha you're aware of** (DB session
  lifecycle vs. generator lifecycle) rather than discovering it via a
  runtime error after the fact.
- **Ask for a genuine behavioral test of any cross-cutting claim** (here:
  "the embedding space is shared across languages") via an actual query in
  the other language, not just a check that the feature exists.
