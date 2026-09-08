"""Semantic search over every past agent run — finds by meaning, not
keyword, reusing the same Chroma-backed pattern as Verity's Claim Research
Library."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..database import get_db
from ..ml import embeddings
from ..rate_limit import rate_limit_ai
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/search", dependencies=[Depends(rate_limit_ai), Depends(verify_csrf)])
def search(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    vector = embeddings.embed_query(query)
    result = vectorstore.query(vector, n_results=10)
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    run_ids = [int(i.split("-")[1]) for i in ids if i.startswith("run-")]
    if not run_ids:
        return []
    rows = db.query(models.AgentRun).filter(models.AgentRun.id.in_(run_ids), models.AgentRun.org_id == user.org_id).all()
    by_id = {r.id: r for r in rows}
    out = []
    for i, dist in zip(ids, distances):
        if not i.startswith("run-"):
            continue
        run_id = int(i.split("-")[1])
        row = by_id.get(run_id)
        if not row:
            continue
        similarity = max(0.0, 1 - dist / 2)
        out.append(
            {
                "id": row.id,
                "question": row.question,
                "final_answer": row.final_answer[:300],
                "status": row.status,
                "similarity": round(similarity * 100, 1),
                "created_at": row.created_at.isoformat(),
            }
        )
    out.sort(key=lambda r: r["similarity"], reverse=True)
    return out
