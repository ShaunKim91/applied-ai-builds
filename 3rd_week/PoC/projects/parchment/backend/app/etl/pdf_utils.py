"""PDF text extraction, with an automatic scanned-PDF OCR fallback.

Uses `pypdf`-based text extraction for the common case (a normal,
text-layer PDF). There's also the "scanned PDF" case — a PDF that's
really just page images with no text layer, where `pypdf` extracts
near-nothing. This module handles that case directly rather than
leaving it as a known gap: if extraction yields fewer than
`settings.pdf_scanned_fallback_char_threshold` characters, each page is
rendered to an image (`pdf2image`, backed by the `poppler-utils` system
package) and read with the SAME Tesseract engine already used by the
Receipts tab (`ml/ocr.py`) — a deliberate cross-feature reuse of one model
rather than a second, redundant OCR path.
"""
from ..config import settings


def extract_text(pdf_path: str) -> dict:
    """Returns {"text": str, "char_count": int, "used_scanned_fallback": bool}."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if len(text.strip()) >= settings.pdf_scanned_fallback_char_threshold:
        return {"text": text, "char_count": len(text), "used_scanned_fallback": False}

    # Likely a scanned/image-only PDF — fall back to page-image OCR.
    ocr_text = _ocr_scanned_pdf(pdf_path)
    return {"text": ocr_text, "char_count": len(ocr_text), "used_scanned_fallback": True}


def _ocr_scanned_pdf(pdf_path: str) -> str:
    import tempfile

    from pdf2image import convert_from_path

    from ..ml import ocr as ocr_ml

    pages_text = []
    with tempfile.TemporaryDirectory() as tmpdir:
        images = convert_from_path(pdf_path, dpi=200, output_folder=tmpdir, fmt="png")
        for img in images:
            img_path = f"{tmpdir}/page.png"
            img.save(img_path)
            pages_text.append(ocr_ml.image_to_text(img_path))
    return "\n".join(pages_text)
