"""HTML table scraping — BeautifulSoup + pandas.

Always local, no LLM/cloud option: parsing an HTML `<table>` into rows and
columns is a deterministic, well-solved problem that doesn't benefit from
an AI model (no `engine` parameter on this path, unlike the Receipts/PDF
tabs).
"""
import httpx
import pandas as pd
from bs4 import BeautifulSoup

SAMPLE_HTML_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)"
SAMPLE_HTML_LABEL = "Wikipedia: List of countries by GDP (nominal)"
# CC BY-SA 4.0 — Wikipedia contributors. Live-fetched for parsing, not
# redistributed as a bundled dataset; see data/SOURCES.md for attribution.

# A conservative default: identify the request and respect a reasonable
# per-request pause if this were ever looped over multiple pages (standard
# scraping-etiquette practice) — this app only ever fetches one page per
# request, triggered by an explicit user action, never a background crawl.
_HEADERS = {"User-Agent": "Parchment-Week3-PoC/1.0 (educational demo; single-page fetch per request)"}


def fetch_and_parse_tables(url: str, max_tables: int = 5) -> dict:
    """Fetches `url` and parses every <table> found into a pandas DataFrame.
    Returns {"tables": [{"headers": [...], "rows": [[...]], "csv": str}], ...}."""
    resp = httpx.get(url, headers=_HEADERS, timeout=20.0, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables_out = []
    for table in soup.find_all("table")[:max_tables]:
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if len(rows) < 2:
            continue  # skip layout tables with no real header+data structure
        headers, *body = rows
        # pandas.DataFrame needs uniform row width — pad/truncate defensively
        # (real-world HTML tables often have colspan-driven irregular rows).
        width = len(headers)
        body = [r[:width] + [""] * (width - len(r)) for r in body]
        df = pd.DataFrame(body, columns=headers)
        tables_out.append(
            {
                "headers": headers,
                "rows": df.values.tolist(),
                "row_count": len(df),
                "csv": df.to_csv(index=False),
            }
        )
    return {"url": url, "table_count": len(tables_out), "tables": tables_out}
