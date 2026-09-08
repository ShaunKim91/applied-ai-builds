import io
import json
import os
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.sample_catalog import ensure_sample_images
from ..media import media_url
from ..ml import embeddings as emb_ml
from ..ml import vision as vision_ml
from ..security import get_current_user
from .. import vectorstore

router = APIRouter(prefix="/api/vision", tags=["vision"])


def _index_for_search(item: models.CatalogItem) -> None:
    """Best-effort: index the classified item for semantic search. Failures
    here must never break the classification response itself."""
    try:
        vector = emb_ml.embed_passage(item.description)
        vectorstore.upsert(
            str(item.id), item.description, vector, {"label": item.predicted_label, "item_id": item.id}
        )
    except Exception:
        pass


@router.get("/samples")
def list_samples():
    paths = ensure_sample_images(settings.data_dir)
    return {"samples": [{"filename": os.path.basename(p), "url": media_url(p)} for p in paths]}


@router.post("/classify")
async def classify(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    content = await file.read()
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception:
        raise HTTPException(400, "Invalid or unsupported image file")

    with timed() as elapsed:
        results = vision_ml.classify_image(image)
    latency = elapsed()

    out_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = f"{int(time.time() * 1000)}_{os.path.basename(file.filename or 'upload.png')}"
    save_path = os.path.join(out_dir, safe_name)
    with open(save_path, "wb") as f:
        f.write(content)

    top = results[0]
    item = models.CatalogItem(
        owner_id=user.id,
        source="upload",
        filename=file.filename or safe_name,
        image_path=save_path,
        predicted_label=top["label"],
        confidence=top["confidence"],
        top5_json=json.dumps(results),
        description=f"{top['label']} product photo",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _index_for_search(item)

    log_action(db, user, "vision.classify", model_used=settings.vit_model, detail=top["label"], latency_ms=latency)
    return {"id": item.id, "image_url": media_url(item.image_path), "predictions": results, "latency_ms": round(latency, 1)}


@router.post("/classify-sample/{filename}")
def classify_sample(
    filename: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    path = os.path.join(settings.data_dir, "sample_images", filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Sample image not found — call GET /api/vision/samples first")

    image = Image.open(path)
    with timed() as elapsed:
        results = vision_ml.classify_image(image)
    latency = elapsed()

    top = results[0]
    item = models.CatalogItem(
        owner_id=user.id,
        source="sample",
        filename=filename,
        image_path=path,
        predicted_label=top["label"],
        confidence=top["confidence"],
        top5_json=json.dumps(results),
        description=f"{top['label']} product photo ({filename})",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _index_for_search(item)

    log_action(db, user, "vision.classify_sample", model_used=settings.vit_model, detail=filename, latency_ms=latency)
    return {"id": item.id, "image_url": media_url(item.image_path), "predictions": results, "latency_ms": round(latency, 1)}


@router.get("/catalog")
def catalog(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    items = db.query(models.CatalogItem).order_by(models.CatalogItem.created_at.desc()).limit(50).all()
    return [
        {
            "id": i.id,
            "filename": i.filename,
            "label": i.predicted_label,
            "confidence": i.confidence,
            "source": i.source,
            "image_url": media_url(i.image_path),
            "top5": json.loads(i.top5_json) if i.top5_json else [],
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]
