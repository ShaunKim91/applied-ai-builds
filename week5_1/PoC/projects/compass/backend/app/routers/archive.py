"""Research archive — every past report is embedded (see routers/research.py's
send_query) into the shared vector store, so "search my past research" is a
real semantic lookup, not a keyword LIKE query. This is Compass's SQL+VectorDB
requirement put to direct product use, distinct from Week4's use of the same
pairing (which indexed a fixed document corpus, not the app's own output).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..database import get_db
from ..ml import embeddings
from ..security import get_current_user

router = APIRouter(prefix="/api/archive", tags=["archive"])


class ArchiveSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
def search_archive(
    payload: ArchiveSearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    vector = embeddings.embed_query(payload.query)
    hits = vectorstore.query(vector, top_k=payload.top_k)
    results = []
    for h in hits:
        report_id = h["metadata"].get("report_id")
        entry = db.get(models.ReportEntry, report_id) if report_id else None
        if not entry:
            continue
        results.append(
            {
                "report_id": entry.id,
                "session_id": entry.session_id,
                "query": entry.query,
                "report_excerpt": entry.report_text[:280],
                "similarity": h["similarity"],
                "created_at": entry.created_at.isoformat(),
            }
        )
    return results
