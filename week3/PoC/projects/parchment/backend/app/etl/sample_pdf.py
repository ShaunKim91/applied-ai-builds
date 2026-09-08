"""Downloads a real public-domain PDF sample for the PDF Summarizer tab.

Source: the Federal Reserve's Monetary Policy Report (semiannual report to
Congress) — an official U.S. federal government publication, public domain
under U.S. copyright law (17 U.S.C. §105), same public-domain reasoning
already applied to the FOMC minutes used in the Week2 PoC. URL verified
reachable before being hardcoded here.
"""
import os

SAMPLE_PDF_URL = "https://www.federalreserve.gov/monetarypolicy/files/20240705_mprfullreport.pdf"
SAMPLE_PDF_FILENAME = "fed_monetary_policy_report_2024-07-05.pdf"
SAMPLE_PDF_LABEL = "Fed Monetary Policy Report (Jul 2024)"


def ensure_sample_pdf(data_dir: str) -> str | None:
    """Downloads the sample PDF once (idempotent). Returns the local path,
    or None if the download failed (e.g. offline) — callers should treat a
    missing sample gracefully rather than crash the whole bootstrap, same
    "isolated step" discipline as the Week1/2 PoCs' `_warm_step()`."""
    import httpx

    out_dir = os.path.join(data_dir, "sample_pdf")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, SAMPLE_PDF_FILENAME)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    try:
        with httpx.stream("GET", SAMPLE_PDF_URL, timeout=30.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(path, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        return path
    except Exception:
        return None
