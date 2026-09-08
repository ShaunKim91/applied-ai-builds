from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..ml import embeddings as emb_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(5, ge=1, le=20)


@router.get("/status")
def status(user: models.User = Depends(get_current_user)):
    return {"backend": vectorstore.backend_name()}


@router.post("")
def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    with timed() as elapsed:
        vector = emb_ml.embed_query(payload.query)
        results = vectorstore.query(vector, top_k=payload.top_k)
    latency = elapsed()

    log_action(db, user, "search.semantic", model_used=settings.embedding_model, detail=payload.query, latency_ms=latency)
    return {"results": results, "backend": vectorstore.backend_name(), "latency_ms": round(latency, 1)}
