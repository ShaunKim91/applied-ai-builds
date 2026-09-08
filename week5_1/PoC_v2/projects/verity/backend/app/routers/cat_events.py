"""Catastrophe/weather events as first-class objects — an analyst pins a
named event and every research session tagged to it rolls up underneath."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import get_current_user, verify_csrf

router = APIRouter(prefix="/api/cat-events", tags=["cat-events"])


class CatEventIn(BaseModel):
    name: str
    event_type: str = "other"
    region: str = ""
    occurred_on: str  # ISO date
    description: str = ""


def _dict(e: models.CatEvent) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "event_type": e.event_type,
        "region": e.region,
        "occurred_on": e.occurred_on.date().isoformat() if isinstance(e.occurred_on, dt.datetime) else str(e.occurred_on),
        "description": e.description,
        "created_at": e.created_at.isoformat(),
    }


@router.get("")
def list_events(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.CatEvent).filter(models.CatEvent.org_id == user.org_id).order_by(models.CatEvent.occurred_on.desc()).all()
    return [_dict(r) for r in rows]


@router.post("", dependencies=[Depends(verify_csrf)])
def create_event(payload: CatEventIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        occurred = dt.datetime.fromisoformat(payload.occurred_on)
    except ValueError:
        raise HTTPException(400, "occurred_on must be an ISO date (YYYY-MM-DD)")
    event = models.CatEvent(
        org_id=user.org_id,
        name=payload.name,
        event_type=payload.event_type,
        region=payload.region,
        occurred_on=occurred,
        description=payload.description,
        created_by_id=user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _dict(event)


@router.get("/{event_id}/sessions")
def event_sessions(event_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    event = db.get(models.CatEvent, event_id)
    if not event or event.org_id != user.org_id:
        raise HTTPException(404, "Event not found")
    rows = (
        db.query(models.ResearchSession)
        .filter(models.ResearchSession.cat_event_id == event_id)
        .order_by(models.ResearchSession.created_at.desc())
        .all()
    )
    return [
        {"id": s.id, "title": s.title, "claim_number": s.claim_number, "jurisdiction": s.jurisdiction, "created_at": s.created_at.isoformat()}
        for s in rows
    ]
