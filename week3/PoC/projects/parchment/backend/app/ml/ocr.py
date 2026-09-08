"""Model 1 — classical OCR via Tesseract (LSTM engine, Tesseract 4+).

This is the "trained/classical" side of the comparison this tab draws: a
purpose-built neural OCR engine that reads pixels into text, then a
regex/local-LLM pass structures that text into fields. Contrast with
vlm.py, which reads the same image directly with a general-purpose
multimodal model and answers questions about it without an OCR step at
all — the two are shown side by side in the Receipts tab.

Tesseract is installed as a system binary (`tesseract-ocr` +
`tesseract-ocr-kor` apt packages, see docker/Dockerfile) and driven via the
`pytesseract` Python binding.
"""
import re
import shutil
import threading

_lock = threading.Lock()
_checked = False
_available = False


def _check() -> bool:
    global _checked, _available
    if not _checked:
        with _lock:
            if not _checked:
                _available = shutil.which("tesseract") is not None
                _checked = True
    return _available


def is_available() -> bool:
    return _check()


def image_to_text(image_path: str, lang: str = "eng") -> str:
    """Run Tesseract OCR on an image file. `lang` accepts Tesseract language
    codes ("eng", "kor", or "eng+kor" for mixed documents)."""
    import pytesseract
    from PIL import Image

    if not _check():
        raise RuntimeError(
            "tesseract binary not found on PATH — install the tesseract-ocr "
            "apt package (see docker/Dockerfile)."
        )
    with Image.open(image_path) as img:
        return pytesseract.image_to_string(img, lang=lang)


# --- Regex-based receipt structuring (a common baseline approach for this
# kind of task — used here as the "classic" structuring path; llm.py's
# local Qwen model provides a smarter, LLM-based structuring alternative
# that the Receipts router runs alongside it) ---
_ITEM_RE = re.compile(r"^(?P<name>[A-Za-z가-힣][\w가-힣 .'-]{1,40}?)\s+\$?(?P<price>\d+\.\d{2})\s*$", re.MULTILINE)
_TOTAL_RE = re.compile(r"(?:total|합계)\s*[:\-]?\s*\$?(?P<total>\d+\.\d{2})", re.IGNORECASE)


def regex_structure(ocr_text: str) -> dict:
    """A deliberately simple regex pass over OCR text — a typical
    `_ITEM_RE`/`_TOTAL_RE` first-pass approach. Returns whatever it can find;
    an empty result is a legitimate outcome for a receipt layout the regex
    doesn't recognize (the local-LLM structuring path is the fallback for
    exactly this case)."""
    items = [{"name": m.group("name").strip(), "price": float(m.group("price"))} for m in _ITEM_RE.finditer(ocr_text)]
    total_match = _TOTAL_RE.search(ocr_text)
    return {
        "items": items,
        "total": float(total_match.group("total")) if total_match else None,
        "method": "regex",
    }


def model_info() -> dict:
    return {"model_id": "tesseract (LSTM OCR engine)", "loaded": is_available()}
