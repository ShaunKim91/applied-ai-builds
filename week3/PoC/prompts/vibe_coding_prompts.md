# Vibe-Coding Prompt Playbook — Parchment (Week3 PoC)

This is the prompt sequence a student could actually use — with an AI coding
tool such as Claude Code — to reproduce a project like Parchment from
scratch. It mirrors the Week1/11 PoCs' own playbooks
(`../../week1/PoC/prompts/`, `../../week2/PoC/prompts/`) in structure,
with one new phase this round: an explicit UI-differentiation step.

## Phase 0 — Research before touching code

> Summarize this week's target technique set (computer vision concepts,
> image-to-JSON extraction, PDF parsing + summarization, HTML table
> scraping) and survey a few reasonable library/model choices for each. Also
> check what UI/visual design the Week1 and Week2 PoCs in this repo
> already used — I want this new one to look meaningfully different, not
> just be built on the same template.

**Why the second half matters this round specifically**: the user's actual
request was "make the UI different this time." Diffing the previous two
PoCs' `tailwind.config.js`/`index.css` files (they turned out to be 100%
identical) is what turned a vague instruction into a concrete, checkable
target — "don't reuse this exact palette/layout" — rather than something
that could be quietly ignored.

## Phase 0.5 — Explicitly reuse working infrastructure code, redesign the visual layer

> Copy VoxIQ's `security.py`, auth router, shape-only email validator,
> `_warm_step()` bootstrap pattern, readiness-probe endpoint, and Docker/
> script skeletons — these are infrastructure, not visual design, and
> reusing them is free correctness. But do NOT copy `tailwind.config.js`,
> `index.css`, or `Layout.tsx` — design new tokens (different font pairing,
> different color palette, different navigation pattern) and justify each
> choice against the project's actual topic.

**Why split infrastructure reuse from visual-design reuse**: they're
independent decisions. Blindly copying *everything* from a working
template (including its CSS) is what produced two visually-identical PoCs
in the first place; the fix isn't "don't reuse the template" (that would
throw away real, working, already-debugged code) — it's "reuse the parts
that are correctness, redesign the parts that are branding."

## Phase 1 — Plan before building, and make the redesign concrete in the plan

> Design a Week3 PoC combining all three of the week's topics (image/
> multimodal extraction, PDF parsing/summarization, HTML table scraping)
> into one coherent product. Same non-negotiables as before: FastAPI +
> React/TypeScript, Docker with auto-detected free ports, SQL + vector DB,
> real/synthetic data with auto-download scripts, auth + admin console, at
> least 2 AI models. Additionally, write out the specific visual
> differentiation as a table: old font vs. new font, old palette vs. new
> palette, old nav pattern vs. new nav pattern — not just "make it look
> different" as a vague aspiration.

**Why a table, specifically**: "different" is unverifiable as prose; a
before/after table of concrete token values (a specific hex code, a
specific font name, a specific layout primitive) is something you can
actually check was followed once the build is done.

## Phase 2 — Verify facts with live tools, not memory

> Before finalizing model and dataset choices: confirm the exact
> HuggingFace model IDs for a small local vision-language model and a
> dedicated summarization model actually exist and match their claimed
> parameter counts — don't rely on a remembered name. Confirm the exact
> public PDF and HTML-table URLs you're proposing to hardcode are reachable
> and contain what you think they contain.

**Why**: exactly the same reasoning as the Week1/11 PoCs' own Phase 2 —
and here it specifically caught that Google Fonts' correct family name is
case- and hyphenation-sensitive, and that a Wikipedia page's table
structure needed to be confirmed (column headers, row count) before being
described in documentation as a "verified" sample.

## Phase 3 — Scaffold, reusing infrastructure files verbatim where safe

> Create the directory scaffolding, then copy (not rewrite) every backend
> file that has no project-specific business logic:
> `security.py`, `database.py`, `state.py`, `audit.py`, `media.py`,
> `vectorstore.py`, the auth router, `embeddings.py`, `llm.py`. Write new
> business-logic modules (`ocr.py`, `vlm.py`, `summarizer.py`, `dedupe.py`)
> and new routers from scratch, since those encode this week's actual new
> ideas.

## Phase 4 — Backend, one layer at a time

> Implement in order, pausing after each: (1) config.py + models.py; (2)
> the ML wrappers, including a deliberate "show two approaches side by
> side" feature (classic OCR+regex vs. a local VLM reading the same image)
> — don't just implement one path and call it done; (3) the ETL helpers
> (synthetic receipt generation, real-PDF download, scanned-PDF OCR
> fallback reusing the SAME OCR model as the receipts feature — look for
> cross-feature model reuse opportunities before adding a second, redundant
> model); (4) the routers, each writing to `audit_logs`.

## Phase 5 — Frontend: new design tokens first, then pages

> Before writing any page component, write the new `tailwind.config.js` and
> `index.css` — new font pairing (a serif for headings via Google Fonts,
> kept as the system sans for body text), new color tokens (a palette that
> actually relates to this week's theme, not an arbitrary different hue),
> a new elevation/shadow language, and a new navigation shape (top tabs
> instead of a sidebar). Then build pages against those tokens — never
> introduce a raw hex color or an ad hoc font-family in a page component.

**Why tokens before pages**: writing pages first and "reskinning" after
tends to leave raw values scattered through components — token discipline
(interface-craft's primitive→semantic→component layering) only works if
it's the starting point, not a retrofit.

## Phase 6 — Containerize

> Same multi-stage Dockerfile pattern as before, with this week's specific
> system dependencies: `tesseract-ocr` (+ a language pack matching the
> project's bilingual UI) and `poppler-utils` (the scanned-PDF-to-image
> fallback's actual rendering backend). Keep the `TORCH_INDEX` build-arg
> pattern in `docker-compose.yml`, not passed ad hoc.

## Phase 7 — Prove it actually works

> Write `verify_e2e.py` covering every feature, INCLUDING a genuine
> functional test of anything that claims to detect something — e.g.
> literally reprocess the same sample document twice and assert the second
> run is flagged as a duplicate, rather than only asserting the endpoint
> returns 200.

**Why this specific test matters**: an endpoint that always returns
`is_duplicate: false` would still pass a shallow "does it respond" check.
Testing the actual claimed behavior (reprocessing something identical
trips the detector) is what makes the E2E suite prove the feature works,
not just that it doesn't crash.

## Phase 8 — Document with facts already in hand, not invented ones

> Write architecture.md, flowchart.md, and docs/guide.html using only
> facts already established — the real verify_e2e.sh output, the real
> measured bootstrap timing, the real dataset citations from Phase 2, and
> the specific visual-differentiation table from Phase 1. Where a claim is
> an estimate (e.g. production cost), label it explicitly as one.

## General prompting habits used throughout this build

- **Turn a vague stylistic request into a checkable diff.** "Make the UI
  different" became "here is exactly what's identical between the last two
  projects, and here is exactly what will differ this time" before any
  code was written.
- **Separate "reuse for correctness" from "reuse because it's easy."**
  Infrastructure code (auth, bootstrap, readiness) should be copied
  wholesale; anything that defines the product's identity (visual design,
  naming, the specific feature comparison shown) should be redesigned even
  when copying would technically work.
- **Ask for a genuine behavioral test of any "smart" feature**, not just a
  200-OK check — a duplicate detector, a numeric verifier, or a fallback
  path all need a test that actually exercises the claimed behavior.
- **Name exact model IDs already validated elsewhere in this project series**
  (`Qwen/Qwen2.5-0.5B-Instruct`, `sentence-transformers/all-MiniLM-L6-v2`)
  and verify any *new* model ID's existence/specs before committing to it.
