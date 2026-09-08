# Debug Log — Lucent (Week4 PoC)

Real issues only, found via actual container bootstrap logs and live E2E/manual
testing against the running container — never fabricated. Each entry links a
symptom actually observed to a root cause actually confirmed in the code.

## Fixed code bugs

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-korean-wikipedia-403-missing-user-agent.md) | Korean Wikipedia fetch 403s (missing User-Agent), and its failure silently blocked indexing of the *entire* English 85-essay corpus too | High | Fixed, re-verified |
| [02](issue-02-groundedness-badge-vanishes-on-history-reload.md) | Groundedness badge renders live but silently vanishes when a chat session's history is reloaded (flat vs. nested field-shape mismatch between the SSE event and the REST history endpoint) | Medium | Fixed, re-verified |
| [03](issue-03-federalist-70-duplicate-title.md) | Two real, distinct Federalist No. 70 textual variants (a genuine Gutenberg-source editorial feature, not a parsing bug) shared one identical, ambiguous document title | Low | Fixed, re-verified |

## Real findings that are not code bugs (documented, not "fixed")

These were surfaced by the same live-testing pass but are genuine
characteristics of the retrieval method chosen, not defects to patch —
recorded here in the interest of the same "no hallucinated numbers, no
hidden failures" discipline used throughout this project.

- **Small bi-encoder embeddings can under-rank an exact-entity-number
  query.** Asking "What does Federalist No. 51 argue about checks and
  balances?" placed the actual Federalist No. 51 document at bi-encoder
  rank 29 of 40 candidates — outside the `top_k=5` rerank pool — so it
  never reached the LLM as a source. The system's designed response to
  this ("the provided sources don't contain the answer") fired correctly;
  it did not hallucinate a plausible-sounding but wrong answer. Full
  measurement and discussion: `projects/lucent/docs/guide.html` → Known
  Limitations & Roadmap.
  - Cross-checked the reverse case with a topic-phrased (not
    number-phrased) query — "checks and balances separation of powers
    ambition counteract ambition" — where Federalist No. 51 ranks 5th
    under the bi-encoder alone and **1st** after cross-encoder reranking,
    confirming the reranker itself works correctly whenever the right
    document is at least inside the first-stage candidate pool.
