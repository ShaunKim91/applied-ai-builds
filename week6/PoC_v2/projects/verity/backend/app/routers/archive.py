"""The Claim Research Library — semantic search over every past report,
filterable by claim number / jurisdiction, reframing the old Compass
Archive with the metadata tags Dana's actual job is organized around."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..database import get_db
from ..ml import embeddings
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/archive", tags=["archive"])


@router.post("/search", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def search(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    vector = embeddings.embed_query(query)
    result = vectorstore.query(vector, n_results=10)
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    entry_ids = [int(i.split("-")[1]) for i in ids if i.startswith("entry-")]
    if not entry_ids:
        return []
    rows = db.query(models.ReportEntry).filter(models.ReportEntry.id.in_(entry_ids), models.ReportEntry.org_id == user.org_id).all()
    by_id = {r.id: r for r in rows}
    out = []
    for i, dist in zip(ids, distances):
        if not i.startswith("entry-"):
            continue
        entry_id = int(i.split("-")[1])
        row = by_id.get(entry_id)
        if not row:
            continue
        similarity = max(0.0, 1 - dist / 2)
        out.append(
            {
                "id": row.id,
                "query": row.query,
                "report_text": row.report_text[:400],
                "mode": row.mode,
                "claim_number": row.claim_number,
                "jurisdiction": row.jurisdiction,
                "similarity": round(similarity * 100, 1),
                "created_at": row.created_at.isoformat(),
            }
        )
    out.sort(key=lambda r: r["similarity"], reverse=True)
    return out
