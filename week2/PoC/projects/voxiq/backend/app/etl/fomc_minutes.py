"""Downloads real U.S. Federal Reserve (FOMC) meeting minutes to build a
genuine "historical meeting archive" for Knowledge Search — these documents
literally are meeting minutes, which fits VoxIQ's theme far better than
generic filler text, and they are real government-published records.

Source: Federal Reserve Board, https://www.federalreserve.gov/monetarypolicy/
  URL pattern: fomcminutes{YYYYMMDD}.htm, where the date is the *second* day
  of each two-day FOMC meeting. As official publications of a U.S. federal
  instrumentality, these carry no copyright notice and are treated as
  public-domain government works (17 U.S.C. §105 analog); the Federal
  Reserve publishes them for unrestricted public use.
  Three of the seven dates below were fetched and manually confirmed to
  return real minutes content before being hardcoded here; the rest follow
  the same, now-verified, URL pattern. The download step skips (does not
  hard-fail on) any date that 404s or returns unexpectedly short content —
  meeting dates can occasionally shift.

Also provides `chunk_text()` — a simple word-count chunker with overlap
(a standard technique for keeping retrieval passages a manageable, useful
size) so a ~9,000-word minutes document becomes multiple retrievable,
appropriately-sized passages instead of one enormous one.
"""
import os

import requests
from bs4 import BeautifulSoup

FOMC_DATES = ["20240131", "20240320", "20240501", "20240612", "20240731", "20240918", "20250129"]
BASE_URL = "https://www.federalreserve.gov/monetarypolicy/fomcminutes{date}.htm"
_HEADERS = {"User-Agent": "Mozilla/5.0 (educational PoC data fetch; VoxIQ)"}


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def ensure_fomc_minutes(data_dir: str) -> list[dict]:
    out_dir = os.path.join(data_dir, "fomc_minutes")
    os.makedirs(out_dir, exist_ok=True)
    docs = []

    for date in FOMC_DATES:
        fname = f"fomc_{date}.txt"
        fpath = os.path.join(out_dir, fname)
        if not os.path.exists(fpath):
            try:
                resp = requests.get(BASE_URL.format(date=date), timeout=30, headers=_HEADERS)
                if resp.status_code == 200:
                    text = _extract_text(resp.text)
                    if len(text) > 500:  # sanity check: real content, not an error/redirect page
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(text)
            except requests.RequestException:
                continue
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                docs.append({"date": date, "filename": fname, "text": f.read()})
    return docs


def chunk_text(text: str, chunk_size: int = 220, overlap: int = 40) -> list[str]:
    """Splits `text` into ~chunk_size-word passages with `overlap` words
    shared between consecutive chunks, so content spanning a chunk boundary
    isn't lost — the standard "panorama photo" overlap-chunking pattern."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks
