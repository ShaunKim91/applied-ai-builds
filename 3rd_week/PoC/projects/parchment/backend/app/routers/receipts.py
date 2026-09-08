import json
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.sample_receipts import RECEIPTS as SAMPLE_RECEIPTS
from ..etl.sample_receipts import ensure_sample_receipts
from ..media import media_url
from ..ml import dedupe as dedupe_ml
from ..ml import llm as llm_ml
from ..ml import ocr as ocr_ml
from ..ml import vlm as vlm_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

STRUCTURE_SYSTEM_PROMPT = (
    "You are a receipt-parsing assistant. You are given raw OCR text from a "
    "receipt photo, which may contain OCR errors. Extract a JSON object with "
    'exactly these keys: {"vendor": string, "items": [{"name": string, '
    '"price": number}], "total": number or null}. If a field is unknown, use '
    "null (or an empty list for items). Output ONLY the JSON object, no "
    "explanation, no markdown fences."
)
VLM_QUESTION = "What store is this receipt from, what items were purchased, and what is the total? Answer briefly."


@router.get("/samples")
def list_samples():
    ensure_sample_receipts(settings.data_dir)
    return {"samples": [{"filename": s["filename"], "label": s["label"]} for s in SAMPLE_RECEIPTS]}


def _process(image_path: str, filename: str, source: str, is_synthetic: bool, db: Session, user) -> models.Receipt:
    receipt = models.Receipt(
        owner_id=user.id, source=source, filename=filename, image_path=image_path, is_synthetic=is_synthetic
    )

    # --- Path A: classic OCR (Tesseract) + regex, then local-LLM structuring ---
    with timed() as elapsed:
        ocr_text = ocr_ml.image_to_text(image_path, lang="eng")
        regex_result = ocr_ml.regex_structure(ocr_text)
        try:
            llm_result = llm_ml.generate(STRUCTURE_SYSTEM_PROMPT, ocr_text, provider="local")
            structured = json.loads(llm_result["text"])
        except Exception:
            structured = regex_result
    receipt.ocr_text = ocr_text
    receipt.ocr_structured_json = json.dumps(structured)
    receipt.ocr_latency_ms = elapsed()
    log_action(db, user, "receipt.ocr_structure", model_used=settings.local_llm_model, latency_ms=receipt.ocr_latency_ms)

    # --- Path B: local VLM reads the image directly, no OCR step ---
    with timed() as elapsed:
        try:
            vlm_answer = vlm_ml.ask_image(image_path, VLM_QUESTION)
        except Exception as exc:  # a VLM load/inference failure shouldn't break the OCR path above
            vlm_answer = f"(VLM unavailable: {exc})"
    receipt.vlm_answer = vlm_answer
    receipt.vlm_latency_ms = elapsed()
    log_action(db, user, "receipt.vlm_read", model_used=settings.vlm_model, latency_ms=receipt.vlm_latency_ms)

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    # --- Duplicate detection (embedding similarity, see ml/dedupe.py) ---
    dupe = dedupe_ml.register_and_check(f"receipt-{receipt.id}", "receipt", ocr_text, {"receipt_id": receipt.id})
    if dupe["is_duplicate"]:
        dup_id = int(dupe["duplicate_of"].split("-")[-1])
        receipt.duplicate_of_id = dup_id
        receipt.duplicate_similarity = dupe["similarity"]
        db.commit()

    return receipt


def _to_dict(r: models.Receipt) -> dict:
    return {
        "id": r.id,
        "filename": r.filename,
        "source": r.source,
        "is_synthetic": r.is_synthetic,
        "image_url": media_url(r.image_path),
        "ocr_text": r.ocr_text,
        "ocr_structured": json.loads(r.ocr_structured_json) if r.ocr_structured_json else None,
        "ocr_latency_ms": round(r.ocr_latency_ms, 1),
        "vlm_answer": r.vlm_answer,
        "vlm_latency_ms": round(r.vlm_latency_ms, 1),
        "duplicate_of_id": r.duplicate_of_id,
        "duplicate_similarity": round(r.duplicate_similarity, 3) if r.duplicate_of_id else None,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/extract")
async def extract_upload(file: UploadFile, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    upload_dir = os.path.join(settings.data_dir, "uploaded_receipts")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".png"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_dir, saved_name)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    receipt = _process(saved_path, file.filename or saved_name, "upload", False, db, user)
    return _to_dict(receipt)


@router.post("/extract-sample/{filename}")
def extract_sample(filename: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    samples = ensure_sample_receipts(settings.data_dir)
    match = next((s for s in samples if s["filename"] == filename), None)
    if not match:
        raise HTTPException(404, "Unknown sample")
    receipt = _process(match["path"], filename, "sample", True, db, user)
    return _to_dict(receipt)


@router.get("")
def list_receipts(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.Receipt).order_by(models.Receipt.created_at.desc()).limit(20).all()
    return [_to_dict(r) for r in rows]
