# Vibe-Coding Prompt Playbook — Compass (Week6 PoC)

This is the prompt sequence a student could actually use — with an AI coding tool such as Claude
Code — to reproduce a project like Compass from scratch. It mirrors the Week1-4 PoCs' own
playbooks in structure, with new phases this round for turning a vague "keep raising the quality
bar every week" request into something buildable, and for building against a search backend a
common reference stack for this pattern assumes (Naver/Gemini) that this build doesn't have keys
for.

## Phase 0 — Research before touching code

> Summarize this week's technical topic (search APIs, embedding-based result reranking,
> search+LLM grounding, a "Vibe Coding" tool-evaluation framework) and a typical baseline
> implementation's exact library/model choices — including checking whether any given reference
> code samples still match what a real, shipped baseline implementation actually does, and whether
> a top-level README's own quick-start commands still work against the current file layout.

**Why the second half matters**: this specifically caught that (a) an introductory teaching example
describes a hash-based toy embedding that a real baseline implementation's actual code never uses
(real `sentence-transformers` models instead), (b) that baseline's default synthesis path calls no
LLM at all despite the reference material assuming an LLM call, and (c) a top-level README's own
quick-start instruction is broken (the real files live under a different path than documented) —
all three found by actually reading and running things, not by trusting the narrative alone.

## Phase 1 — Turn "keep raising the bar" into something specific and checkable

> The brief this round is qualitative: "as weeks go up, keep escalating UI/UX and overall quality."
> Before writing code, name the exact structural deltas versus last week's build (Week4 "Lucent"):
> a new color/typography system (not just new hex values — a new font-pairing *structure*, e.g. two
> fonts becoming three), a new navigation pattern, a first-time default-theme flip, and a genuine
> motion system where the prior week had none. Also name the exact new *product* capability that
> represents "higher value," not just a UI reskin — here, a verification axis the prior week didn't
> have (ghost-citation checking) and a governance feature a typical baseline implementation of this
> pattern never implements (a cost cap).

**Why**: "make it nicer" is unverifiable. A structural, dimension-by-dimension comparison against
the prior week (this build's `architecture.md` §2 and its UI-differentiation table) is something
you can actually check was delivered.

## Phase 2 — Verify facts with live tools, not memory, especially for the parts a common reference stack assumes you have keys for

> Before committing to a search backend: confirm which API keys actually exist in this repo. If a
> common reference vendor for this pattern (here, Naver Search API) isn't available, don't fabricate
> a workaround — find a real, keyless alternative (here: `ddgs`, confirmed live via its PyPI page —
> exact install command, import, method signature, and result-field names) and confirm the
> project's own already-validated cloud vendor (OpenRouter) actually offers a feature that fits this
> week's topic (its web-search plugin) via that vendor's own current docs, not assumed syntax.

**Why**: two real facts were confirmed live this round, not recalled from training data — `ddgs`'s
exact API surface, and OpenRouter's exact web-search request/response shape (`plugins:
[{"id":"web"}]`, `annotations[].url_citation`, real per-request pricing). Getting either wrong from
memory would have produced code that compiles but silently doesn't work.

## Phase 3 — Scaffold, reusing infrastructure files verbatim where safe

> Copy every backend file with no project-specific business logic (`security.py`, `database.py`,
> `audit.py`, `state.py`, `vectorstore.py`, the auth router, `ml/embeddings.py`, `ml/reranker.py`,
> `ml/groundedness.py`, the streaming SSE plumbing in `ml/llm.py`) from the most recent prior
> project. Write new modules only for what's genuinely new this week (`search/web_search.py`,
> `search/rerank_pipeline.py`, `ml/ghost_citation.py`, the OpenRouter web-search-plugin call, cost
> governance).

**Applying a lesson instead of re-discovering it**: while writing the new `_entry_dict()` history-
reload endpoint, deliberately shape its `groundedness` field to match the live SSE event's nested
shape from the start — not because a bug was found, but because the *exact same* flat-vs-nested
mismatch was a real, documented bug in the prior week's PoC (`week4/PoC/debug/issue-02`). Applying
a known lesson proactively is strictly better than reproducing the same bug and "discovering" it
again.

## Phase 4 — Backend: treat a live, unreliable external dependency as a first-class failure mode

> Implement the live web-search call with a standard mock-first fallback pattern — but go one step
> further than a typical introductory version by reporting *which* mode actually served each result
> (`ddgs` vs `mock`) all the way to the database row and the UI, instead of making the fallback
> indistinguishable from a real result.

**Why this matters here specifically**: unlike a local model (which either loads or doesn't, once),
a live scraped search dependency can succeed on one request and fail on the next — the failure mode
is per-request, not per-boot, so the handling needs to be per-request too.

## Phase 5 — Frontend: design tokens first, then verify selector precision before trusting a screenshot

> Before any page component, define the new design tokens (a navy/brass/teal palette, a 3-way font
> system, motion durations/easing grounded in a real reference — not picked by feel). When writing
> the Playwright screenshot script afterward, don't assume a `button:has-text("Search")` or
> `input[placeholder]` selector is unambiguous — check the match count. Two real, non-product
> selector ambiguities were caught this way: a global "command console" input on every page collides
> with each page's own input on a bare placeholder-attribute selector, and `:has-text("Search")`
> substring-matches "**re-search**" (as in "New research") just as much as the actual "Search"
> button.

**Why call this out explicitly**: both looked, from the error message alone, exactly like a
real product bug (a click doing nothing, silently) — verifying with `.count()` and exact-text
locators before concluding "the product is broken" avoided writing up two fabricated bug reports.

## Phase 6 — Containerize

> Same multi-stage Dockerfile pattern as before — this week needs no seed-corpus download step at
> all (the retrieval source is live), so the bootstrap sequence is model-loading + a
> connectivity-check only, one step shorter than Week4's.

## Phase 7 — Prove it actually works, including cost-governance and a rare small-model failure mode

> Write `verify_e2e.py` to include a deterministic regression test for a real, previously-observed
> small-model output shape (a syntactically-valid JSON object followed by one stray extra closing
> brace) rather than only testing the happy path — a live LLM's output is not fully controllable
> request-to-request, so a bug caught once needs a test that reproduces it exactly, not a vague
> "check JSON parses" assertion. Also test the cost-governance cap by actually setting the budget to
> $0 and confirming the paid call is skipped, not just reading the code and assuming it works.

## Phase 8 — Document with facts already in hand, not invented ones

> Write `architecture.md`, `flowchart.md`, and `docs/guide.html` using only facts already
> established — the real `verify_e2e.sh` output, the real bootstrap timing, the real captured
> screenshot evidence of both the ghost-citation feature and the JSON-extraction bug it uncovered.
> Label any cost estimate (production scaling) explicitly as an estimate, distinct from measured
> numbers.

## General prompting habits used throughout this build

- **Convert "keep getting better" into a structural comparison table** before writing any code —
  the single highest-leverage habit for a request phrased as an ongoing quality bar rather than a
  one-time specification.
- **When a common reference vendor for a pattern isn't available, don't substitute silently** — name
  the substitution and its reasoning explicitly in code comments and docs (Naver → `ddgs`, Gemini →
  OpenRouter), so a reader understands this was a deliberate, documented choice, not an oversight.
- **Apply a known bug class proactively across projects**, don't wait to rediscover it — if last
  week's PoC shipped a specific mismatch, check this week's analogous code for the same shape before
  shipping, and say so in the commit/debug trail.
- **Verify a test selector's specificity before trusting what it reports** — an ambiguous locator
  failing looks identical to a real product bug; check match counts before writing up a finding.
