# Issue 03 — Groundedness scoring can be fooled by a hallucinated-but-plausible named authority

**Found**: while visually inspecting a real precedent-brief screenshot generated entirely from the
fictional Cedermoor source corpus, the "Governing Authority" section read **"The Federal Insurance
Office (FIO)"** — a real United States federal body, invented by `Qwen2.5-0.5B-Instruct` despite an
explicit system-prompt instruction to use only the fictional sources it was given, none of which
mention any such office. This is exactly the failure mode Verity's whole grounding pipeline exists
to catch — and it slipped through `groundedness.verify()` completely undetected.

## Root cause

`groundedness.verify()`'s content check computes, per sentence, the maximum cosine similarity
against the retrieved sources' embeddings and passes if enough sentences clear a 0.55 threshold.
Measured directly: the sentence `"Governing Authority: The Federal Insurance Office (FIO) oversees
this requirement."` scored a **perfect 1.0 groundedness** against the real Cedermoor sources (which
say nothing about any federal office) — because it shares the surrounding topical vocabulary
("governing authority", "requirement", insurance-claims register) with the real sources closely
enough for `multilingual-e5-small` to rate it highly similar, even though the specific factual claim
(a fabricated authority name) appears nowhere in the source text. This is the same underlying
embedding-model characteristic as issue-02 (similarity tracks topic, not fact) — surfacing here as a
gap in a *safety* check rather than a *feature*, which makes it materially more serious: it's the
exact failure this whole product exists to prevent, and the automated check gave it a clean pass.

## Fix

Added `ghost_citation.check_entities()` — a second, independent, deterministic check alongside the
existing URL-based ghost-citation check: extract every multi-word Title Case phrase (a crude but
effective proper-noun detector) from the answer, and flag any that don't appear verbatim in the
actual retrieved source text (excluding known labels like the fictional jurisdiction names and the
brief template's own section headers). `"The Federal Insurance Office"` — a real, named, capitalized
multi-word entity that appears in none of the source text — is exactly the shape of thing this catches.
Wired into `routers/research.py` so its result merges into the same `ghost_citations` payload the UI
already renders (`passed` becomes `false` if either the URL check or the entity check fails).

**This is a partial mitigation, not a full fix.** A regex-based proper-noun detector can miss a
hallucinated single-word entity, a lowercase claim, or a fabricated *fact* that doesn't take the
shape of a named authority at all (e.g. a wrong dollar figure or date) — the deeper problem (a small
local model's instruction-following limits, and a sentence-embedding model's topic/fact conflation)
isn't something a downstream regex check fully solves. This is disclosed explicitly, not
papered over — see `docs/guide.html`'s limitations section.

## Verification

- Reproduced directly: fed the exact hallucinated sentence and the real Cedermoor sources to
  `groundedness.verify()`, confirmed the 1.0 false-pass; fed the same pair to the new
  `check_entities()`, confirmed it correctly flags `"The Federal Insurance Office"` as unverified.
- Added `verify_e2e.py::step_entity_hallucination_regression` reproducing this exact scenario as a
  permanent regression test.
- Re-ran the full research flow on a clean rebuild and confirmed the ghost-citation badge correctly
  reads "Unverified citation found" whenever a fabricated entity like this appears, not just for a
  fabricated URL.
