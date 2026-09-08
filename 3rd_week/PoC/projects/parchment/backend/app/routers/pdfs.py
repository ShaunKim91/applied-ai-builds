import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.pdf_utils import extract_text
from ..etl.sample_pdf import SAMPLE_PDF_LABEL, ensure_sample_pdf
from ..ml import dedupe as dedupe_ml
from ..ml import llm as llm_ml
from ..ml import summarizer as summarizer_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])

INSIGHT_SYSTEM_PROMPT = (
    "You are a business analyst. Given a short text summary of a report, "
    "write one plain-language sentence about why it might matter to a "
    "reader who has not read the full document. No markdown, one sentence."
)


@router.get("/sample")
def sample_info():
    path = ensure_sample_pdf(settings.data_dir)
    return {"available": path is not None, "label": SAMPLE_PDF_LABEL}


def _summarize(pdf_path: str, filename: str, source: str, provider: str, db: Session, user) -> models.PdfSummary:
    with timed() as elapsed:
        extraction = extract_text(pdf_path)
    extract_ms = elapsed()

    text = extraction["text"]
    chunk_count = 0
    chunks_summarized = 0
    with timed() as elapsed:
        result = summarizer_ml.summarize_long_text(text) if provider == "local" else None
        if provider == "openrouter":
            llm_out = llm_ml.generate(
                "Summarize the following document text in 3-4 sentences, plain language, no markdown.",
                text[:6000],
                provider="openrouter",
            )
            summary_text = llm_out["text"]
        else:
            summary_text = result["summary"] if result else ""
            chunk_count = result["chunk_count"] if result else 0
            chunks_summarized = result["chunks_summarized"] if result else 0
    summarize_ms = elapsed()

    check = summarizer_ml.numeric_cross_check(summary_text, text)

    row = models.PdfSummary(
        owner_id=user.id,
        source=source,
        filename=filename,
        extracted_chars=extraction["char_count"],
        used_scanned_fallback=extraction["used_scanned_fallback"],
        chunk_count=chunk_count,
        chunks_summarized=chunks_summarized,
        summary_text=summary_text,
        provider=provider,
        numeric_check_passed=check["passed"],
        numeric_check_detail=", ".join(check["unverified"]) if check["unverified"] else "",
        latency_ms=extract_ms + summarize_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db, user, "pdf.summarize",
        model_used=settings.summarizer_model if provider == "local" else settings.openrouter_model,
        detail=f"scanned_fallback={extraction['used_scanned_fallback']}",
        latency_ms=row.latency_ms,
    )

    dupe = dedupe_ml.register_and_check(f"pdf-{row.id}", "pdf", text, {"pdf_id": row.id})
    if dupe["is_duplicate"]:
        row.duplicate_of_id = int(dupe["duplicate_of"].split("-")[-1])
        row.duplicate_similarity = dupe["similarity"]
        db.commit()

    return row


def _to_dict(r: models.PdfSummary) -> dict:
    return {
        "id": r.id,
        "filename": r.filename,
        "source": r.source,
        "extracted_chars": r.extracted_chars,
        "used_scanned_fallback": r.used_scanned_fallback,
        "chunk_count": r.chunk_count,
        "chunks_summarized": r.chunks_summarized,
        "summary_text": r.summary_text,
        "provider": r.provider,
        "numeric_check_passed": r.numeric_check_passed,
        "numeric_check_detail": r.numeric_check_detail,
        "duplicate_of_id": r.duplicate_of_id,
        "duplicate_similarity": round(r.duplicate_similarity, 3) if r.duplicate_of_id else None,
        "latency_ms": round(r.latency_ms, 1),
        "created_at": r.created_at.isoformat(),
    }


class SummarizeSampleRequest(BaseModel):
    use_openrouter: bool = False


@router.post("/summarize")
async def summarize_upload(
    file: UploadFile,
    use_openrouter: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    upload_dir = os.path.join(settings.data_dir, "uploaded_pdfs")
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.pdf")
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    row = _summarize(saved_path, file.filename or "upload.pdf", "upload", "openrouter" if use_openrouter else "local", db, user)
    return _to_dict(row)


@router.post("/summarize-sample")
def summarize_sample(
    payload: SummarizeSampleRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    path = ensure_sample_pdf(settings.data_dir)
    if not path:
        raise HTTPException(503, "Sample PDF could not be downloaded (offline?) — try uploading your own PDF instead.")
    row = _summarize(path, SAMPLE_PDF_LABEL, "sample", "openrouter" if payload.use_openrouter else "local", db, user)
    return _to_dict(row)


@router.get("")
def list_summaries(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.PdfSummary).order_by(models.PdfSummary.created_at.desc()).limit(20).all()
    return [_to_dict(r) for r in rows]
