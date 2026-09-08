import os
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action
from ..config import settings
from ..database import SessionLocal, get_db
from ..jobs import get_job, submit
from ..media import media_url
from ..ml import diffusion as diffusion_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=300)
    steps: int = Field(12, ge=4, le=30)
    guidance_scale: float = Field(7.0, ge=1.0, le=15.0)


@router.post("")
def generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    record = models.GeneratedImage(
        owner_id=user.id,
        prompt=payload.prompt,
        steps=payload.steps,
        guidance_scale=payload.guidance_scale,
        status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_id = record.id
    user_id, user_email = user.id, user.email

    def task():
        session = SessionLocal()
        try:
            rec = session.get(models.GeneratedImage, record_id)
            rec.status = "running"
            session.commit()

            start = time.perf_counter()
            path = diffusion_ml.generate_image(
                payload.prompt,
                payload.steps,
                payload.guidance_scale,
                out_dir=os.path.join(settings.data_dir, "generated"),
            )
            duration = time.perf_counter() - start

            rec.status = "done"
            rec.image_path = path
            rec.duration_seconds = duration
            session.commit()

            fake_user = type("U", (), {"id": user_id, "email": user_email})()
            log_action(
                session,
                fake_user,
                "generate.image",
                model_used=settings.diffusion_model,
                detail=payload.prompt[:200],
                latency_ms=duration * 1000,
            )
            return {"image_path": path, "image_url": media_url(path), "duration_seconds": round(duration, 1)}
        except Exception as exc:
            rec = session.get(models.GeneratedImage, record_id)
            rec.status = "failed"
            rec.error = str(exc)
            session.commit()
            raise
        finally:
            session.close()

    job_id = submit("generate", task)
    return {"job_id": job_id, "record_id": record_id}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/gallery")
def gallery(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    items = db.query(models.GeneratedImage).order_by(models.GeneratedImage.created_at.desc()).limit(30).all()
    return [
        {
            "id": i.id,
            "prompt": i.prompt,
            "status": i.status,
            "image_url": media_url(i.image_path) if i.image_path else None,
            "duration_seconds": i.duration_seconds,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]
