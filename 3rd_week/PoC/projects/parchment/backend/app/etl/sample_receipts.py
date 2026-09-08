"""Synthetic sample receipts for the Receipts tab.

Real receipt images carry real PII (names, card numbers, addresses) — a
well-known risk with this kind of demo data. Rather than source real
receipts (a licensing and privacy problem), this generates a few varied,
clearly-synthetic demo receipts with Pillow, using a small, standard
image-generation technique: a large canvas (560x220) and Pillow's
built-in `ImageFont.load_default(size=22)` (no external font file needed,
verified to work with real Tesseract OCR).

Items use `$X.XX`-formatted prices so they're readable by BOTH structuring
paths shown side by side in the UI: `ml/ocr.py`'s regex parser (which
expects a decimal price) and `ml/vlm.py`'s direct image understanding
(which doesn't care about format at all).
"""
import io
import os

RECEIPTS = [
    {
        "filename": "sample_receipt_cafe.png",
        "label": "Corner Cafe receipt",
        "lines": ["CORNER CAFE (demo)", "Latte      $4.50", "Muffin     $3.25", "TOTAL: $7.75"],
    },
    {
        "filename": "sample_receipt_office.png",
        "label": "Office Supply Co. receipt",
        "lines": [
            "OFFICE SUPPLY CO. (demo)",
            "Notebook   $2.99",
            "Pens       $5.49",
            "Stapler    $8.00",
            "TOTAL: $16.48",
        ],
    },
    {
        "filename": "sample_receipt_hardware.png",
        "label": "Hardware Depot receipt",
        "lines": ["HARDWARE DEPOT (demo)", "Hammer    $12.99", "Nails      $4.25", "TOTAL: $17.24"],
    },
]


def _render(lines: list[str]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.load_default(size=22)  # Pillow >= 10
    except TypeError:
        font = ImageFont.load_default()

    height = 40 + 50 * len(lines)
    img = Image.new("RGB", (560, height), "white")
    draw = ImageDraw.Draw(img)
    y = 16
    for line in lines:
        draw.text((16, y), line, fill="black", font=font)
        y += 50
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure_sample_receipts(data_dir: str) -> list[dict]:
    """Renders each synthetic receipt to disk once (idempotent) and returns
    the sample list with resolved file paths."""
    out_dir = os.path.join(data_dir, "sample_receipts")
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for spec in RECEIPTS:
        path = os.path.join(out_dir, spec["filename"])
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(_render(spec["lines"]))
        results.append({"filename": spec["filename"], "label": spec["label"], "path": path})
    return results
