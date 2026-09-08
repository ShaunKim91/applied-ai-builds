"""The Document Library — a combined, chronological view across all three
document types, with near-duplicate flags surfaced directly (see
ml/dedupe.py for what "duplicate" means here and why it's deliberately NOT
a search/RAG feature)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("")
def library(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    entries = []
    for r in db.query(models.Receipt).order_by(models.Receipt.created_at.desc()).limit(50).all():
        entries.append(
            {
                "id": f"receipt-{r.id}",
                "doc_type": "receipt",
                "label": r.filename,
                "is_duplicate": r.duplicate_of_id is not None,
                "duplicate_of": f"receipt-{r.duplicate_of_id}" if r.duplicate_of_id else None,
                "similarity": round(r.duplicate_similarity, 3) if r.duplicate_of_id else None,
                "created_at": r.created_at.isoformat(),
            }
        )
    for p in db.query(models.PdfSummary).order_by(models.PdfSummary.created_at.desc()).limit(50).all():
        entries.append(
            {
                "id": f"pdf-{p.id}",
                "doc_type": "pdf",
                "label": p.filename,
                "is_duplicate": p.duplicate_of_id is not None,
                "duplicate_of": f"pdf-{p.duplicate_of_id}" if p.duplicate_of_id else None,
                "similarity": round(p.duplicate_similarity, 3) if p.duplicate_of_id else None,
                "created_at": p.created_at.isoformat(),
            }
        )
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    duplicate_count = sum(1 for e in entries if e["is_duplicate"])
    return {"entries": entries, "total": len(entries), "duplicate_count": duplicate_count}
