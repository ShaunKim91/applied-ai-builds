"""History — semantic search over past agent runs, the same
SQL-record + VectorDB-index pairing validated in the Week5_1 "Compass"
PoC's Archive page, applied here to completed agent runs instead of
research reports.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..database import get_db
from ..ml import embeddings
from ..security import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


class HistorySearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
def search_history(
    payload: HistorySearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    vector = embeddings.embed_query(payload.query)
    hits = vectorstore.query(vector, top_k=payload.top_k)
    results = []
    for h in hits:
        run_id = h["metadata"].get("run_id")
        run = db.get(models.AgentRun, run_id) if run_id else None
        if not run or run.owner_id != user.id:
            continue
        results.append(
            {
                "run_id": run.id,
                "question": run.question,
                "final_answer_excerpt": run.final_answer[:280],
                "similarity": h["similarity"],
                "created_at": run.created_at.isoformat(),
            }
        )
    return results
