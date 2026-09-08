"""Downloads and prepares the two seed knowledge-base corpora — one English,
one Korean, on the same topic — so Lucent's cross-lingual retrieval claim
(both share `multilingual-e5-small`'s embedding space) is something a real
question can actually demonstrate, not just assert.

English: The Federalist Papers (85 essays), Project Gutenberg #18 — a work
of the U.S. founding era, public domain. Split into one Document per essay
(a real improvement in citation quality over treating the whole 1.2MB text
as a single source — "Federalist No. 51" is a far more useful citation than
"The Federalist Papers, chunk 40 of 60").

Korean: the Korean Wikipedia article "연방주의자 논집" (the Federalist
Papers) — CC BY-SA 4.0, directly on-topic with the English corpus, chosen
specifically so a Korean-language question has a real chance of retrieving
either the matching Korean source or (if the embedding space is genuinely
shared, as the model claims) the relevant English essay.
"""
import os
import re
from collections import Counter

import httpx

FEDERALIST_URL = "https://www.gutenberg.org/cache/epub/18/pg18.txt"
FEDERALIST_START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
FEDERALIST_END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"
_ESSAY_HEADING_RE = re.compile(r"^No\. ([IVXLCM]+)\.$", re.MULTILINE)
_MIN_ESSAY_CHARS = 400  # filters out any degenerate/false-positive heading match

KO_WIKIPEDIA_TITLE = "연방주의자_논집"
KO_WIKIPEDIA_API = (
    "https://ko.wikipedia.org/w/api.php"
    "?action=query&prop=extracts&explaintext=1&format=json&titles=" + KO_WIKIPEDIA_TITLE
)
# Wikimedia's User-Agent policy (https://meta.wikimedia.org/wiki/User-Agent_policy)
# blocks requests carrying a generic/default client UA (e.g. httpx's own
# "python-httpx/x.x") with a 403 — a descriptive UA is required, no exceptions.
# See debug/issue-01-korean-wikipedia-403-missing-user-agent.md.
_WIKIMEDIA_HEADERS = {"User-Agent": "Lucent-PoC-Week4/1.0 (educational vibe-coding project; no contact endpoint)"}


def parse_federalist_essays(raw: str) -> list[tuple[str, str]]:
    """Returns [(label, text), ...] — one entry per essay, e.g.
    ("Federalist No. I", "For the Independent Journal. ...").

    This regex genuinely matches 86 headings, not 85 — verified against the
    real downloaded text, not a parsing bug: Gutenberg's own transcription
    of eBook #18 includes an editorial note ("There are two slightly
    different versions of No. 70 included here.") and prints both variants
    back-to-back under the identical heading "No. LXX.". Both are real,
    substantial essay text (so _MIN_ESSAY_CHARS correctly does NOT filter
    either one out) — the only real problem was that identical titles made
    the two variants indistinguishable as citations, so duplicates are
    disambiguated below. See debug/issue-03-federalist-70-duplicate-title.md.
    """
    start = raw.find(FEDERALIST_START_MARKER)
    end = raw.find(FEDERALIST_END_MARKER)
    body = raw[start:end] if start != -1 and end != -1 else raw

    matches = list(_ESSAY_HEADING_RE.finditer(body))
    essays = []
    for i, m in enumerate(matches):
        text_start = m.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        essay_text = body[text_start:text_end].strip()
        if len(essay_text) < _MIN_ESSAY_CHARS:
            continue  # degenerate split (e.g. an inline "No. LI" cross-reference, not a real heading)
        essays.append((m.group(1), essay_text))

    numeral_counts = Counter(numeral for numeral, _ in essays)
    seen_so_far: dict[str, int] = {}
    labeled = []
    for numeral, essay_text in essays:
        label = f"Federalist No. {numeral}"
        if numeral_counts[numeral] > 1:
            seen_so_far[numeral] = seen_so_far.get(numeral, 0) + 1
            label += f" (variant {seen_so_far[numeral]} of {numeral_counts[numeral]})"
        labeled.append((label, essay_text))
    return labeled


def fetch_korean_wikipedia_article() -> tuple[str, str] | None:
    """Returns (title, plain_text) or None if the fetch fails — treated as
    an isolated, non-fatal bootstrap step like everything else."""
    resp = httpx.get(KO_WIKIPEDIA_API, timeout=20.0, headers=_WIKIMEDIA_HEADERS)
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    extract = page.get("extract", "").strip()
    if not extract:
        return None
    return ("연방주의자 논집 (Federalist Papers, Korean Wikipedia)", extract)


def ensure_seed_texts_cached(data_dir: str) -> dict:
    """Downloads both corpora to disk once (idempotent) and returns a
    manifest describing what's available — callers (main.py's bootstrap,
    routers/documents.py) decide what to do with it (embed + index)."""
    out_dir = os.path.join(data_dir, "seed_corpus")
    os.makedirs(out_dir, exist_ok=True)

    federalist_path = os.path.join(out_dir, "federalist_papers.txt")
    if not os.path.exists(federalist_path):
        resp = httpx.get(FEDERALIST_URL, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        with open(federalist_path, "w", encoding="utf-8") as f:
            f.write(resp.text)

    korean_path = os.path.join(out_dir, "federalist_papers_ko_wikipedia.txt")
    korean_available = os.path.exists(korean_path)
    if not korean_available:
        # The Korean fetch is an independent, separately-sourced corpus from
        # the English one above (already downloaded and written to disk by
        # this point) — a failure here must NOT take the English corpus down
        # with it. Originally this call was unguarded, so a transient/policy
        # failure on the Korean side (see debug/issue-01) silently prevented
        # the entire seed corpus — all 85 English essays included — from
        # ever being indexed. See debug/issue-01-korean-wikipedia-403-missing-user-agent.md.
        try:
            article = fetch_korean_wikipedia_article()
        except httpx.HTTPError:
            article = None
        if article:
            with open(korean_path, "w", encoding="utf-8") as f:
                f.write(article[1])
            korean_available = True

    return {"federalist_path": federalist_path, "korean_path": korean_path if korean_available else None}
