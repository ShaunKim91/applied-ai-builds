import os
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.audio_samples import ensure_sample_audio
from ..media import media_url
from ..ml import embeddings as emb_ml
from ..ml import whisper_asr
from ..security import get_current_user

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _index_transcript(meeting: models.Meeting) -> None:
    """Best-effort: index the transcript for semantic search. Must never
    break the transcription response itself if it fails."""
    if not meeting.transcript:
        return
    try:
        vector = emb_ml.embed(meeting.transcript)
        vectorstore.upsert(
            f"meeting-{meeting.id}",
            meeting.transcript,
            vector,
            {"source": "meeting", "meeting_id": meeting.id, "filename": meeting.filename},
        )
    except Exception:
        pass


@router.get("/samples")
def list_samples():
    manifest = ensure_sample_audio(settings.data_dir)
    return {"samples": manifest}


def _save_and_transcribe(
    db: Session,
    user: models.User,
    source: str,
    filename: str,
    audio_path: str,
) -> models.Meeting:
    with timed() as elapsed:
        result = whisper_asr.transcribe(audio_path)
    latency = elapsed()

    meeting = models.Meeting(
        owner_id=user.id,
        source=source,
        filename=filename,
        audio_path=audio_path,
        transcript=result["text"],
        detected_language=result["language"],
        transcribe_latency_ms=latency,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    _index_transcript(meeting)

    log_action(db, user, "meetings.transcribe", model_used=f"whisper-{settings.whisper_model}", detail=filename, latency_ms=latency)
    return meeting


@router.post("/transcribe-sample/{filename}")
def transcribe_sample(filename: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    path = os.path.join(settings.data_dir, "sample_audio", filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Sample audio not found — call GET /api/meetings/samples first")
    meeting = _save_and_transcribe(db, user, "sample", filename, path)
    return {
        "id": meeting.id,
        "transcript": meeting.transcript,
        "language": meeting.detected_language,
        "latency_ms": round(meeting.transcribe_latency_ms, 1),
    }


@router.post("/transcribe")
async def transcribe_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    content = await file.read()
    out_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = f"{int(time.time() * 1000)}_{os.path.basename(file.filename or 'audio')}"
    save_path = os.path.join(out_dir, safe_name)
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        meeting = _save_and_transcribe(db, user, "upload", file.filename or safe_name, save_path)
    except Exception as exc:
        raise HTTPException(400, f"Could not transcribe this file: {exc}")

    return {
        "id": meeting.id,
        "transcript": meeting.transcript,
        "language": meeting.detected_language,
        "latency_ms": round(meeting.transcribe_latency_ms, 1),
    }


@router.get("")
def list_meetings(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    meetings = db.query(models.Meeting).order_by(models.Meeting.created_at.desc()).limit(50).all()
    return [
        {
            "id": m.id,
            "filename": m.filename,
            "source": m.source,
            "transcript": m.transcript,
            "language": m.detected_language,
            "audio_url": media_url(m.audio_path),
            "latency_ms": round(m.transcribe_latency_ms, 1),
            "created_at": m.created_at.isoformat(),
        }
        for m in meetings
    ]
