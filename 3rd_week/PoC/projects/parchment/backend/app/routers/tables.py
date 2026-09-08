from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..database import get_db
from ..etl.html_utils import SAMPLE_HTML_LABEL, SAMPLE_HTML_URL, fetch_and_parse_tables
from ..security import get_current_user

router = APIRouter(prefix="/api/tables", tags=["tables"])


@router.get("/sample")
def sample_info():
    return {"url": SAMPLE_HTML_URL, "label": SAMPLE_HTML_LABEL}


class ParseRequest(BaseModel):
    url: str


@router.post("/parse")
def parse(payload: ParseRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    with timed() as elapsed:
        try:
            result = fetch_and_parse_tables(payload.url)
        except Exception as exc:
            raise HTTPException(400, f"Could not fetch/parse that URL: {exc}") from exc
    latency_ms = elapsed()

    if result["table_count"] == 0:
        raise HTTPException(422, "No parseable <table> elements found on that page.")

    first = result["tables"][0]
    row = models.HtmlScrape(
        owner_id=user.id,
        source_url=payload.url,
        table_count=result["table_count"],
        row_count=first["row_count"],
        column_headers_json=str(first["headers"]),
        preview_csv=first["csv"][:5000],
        latency_ms=latency_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_action(db, user, "table.parse", model_used="beautifulsoup+pandas", latency_ms=latency_ms)

    return {"id": row.id, "latency_ms": round(latency_ms, 1), **result}


@router.get("")
def list_scrapes(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.HtmlScrape).order_by(models.HtmlScrape.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "source_url": r.source_url,
            "table_count": r.table_count,
            "row_count": r.row_count,
            "latency_ms": round(r.latency_ms, 1),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
