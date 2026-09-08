"""Knowledge-base management: the seed corpora (indexed once at bootstrap)
plus user-uploaded documents (indexed on demand here)."""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, vectorstore
from ..config import settings
from ..database import SessionLocal, get_db
from ..etl.chunking import chunk_text
from ..etl.seed_corpus import ensure_seed_texts_cached, parse_federalist_essays
from ..ml import embeddings
from ..security import get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _index_document(db: Session, title: str, text: str, language: str, source: str, owner_id: int | None) -> models.Document:
    chunks = chunk_text(text)
    doc = models.Document(
        owner_id=owner_id, title=title, source=source, language=language,
        char_count=len(text), chunk_count=len(chunks),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if chunks:
        vectors = embeddings.embed_passages(chunks)
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            vectorstore.upsert(
                f"doc-{doc.id}-chunk-{i}", chunk, vector,
                {"document_id": doc.id, "chunk_index": i, "title": title, "language": language},
            )
    return doc


def index_seed_corpus() -> dict:
    """Called once from main.py's startup bootstrap (isolated _warm_step).
    Idempotent at the file-cache level (ensure_seed_texts_cached), but will
    re-create Document rows if called again with an empty DB — safe to call
    exactly once per fresh database, which is how the bootstrap uses it."""
    db = SessionLocal()
    try:
        if db.query(func.count(models.Document.id)).scalar() > 0:
            return {"skipped": "documents already indexed"}

        manifest = ensure_seed_texts_cached(settings.data_dir)
        essays_indexed = 0
        with open(manifest["federalist_path"], encoding="utf-8") as f:
            raw = f.read()
        for label, essay_text in parse_federalist_essays(raw):
            _index_document(db, label, essay_text, "en", "seed", None)
            essays_indexed += 1

        korean_indexed = False
        if manifest["korean_path"]:
            with open(manifest["korean_path"], encoding="utf-8") as f:
                ko_text = f.read()
            _index_document(db, "연방주의자 논집 (Korean Wikipedia)", ko_text, "ko", "seed", None)
            korean_indexed = True

        return {"essays_indexed": essays_indexed, "korean_indexed": korean_indexed}
    finally:
        db.close()


def _to_dict(d: models.Document) -> dict:
    return {
        "id": d.id, "title": d.title, "source": d.source, "language": d.language,
        "char_count": d.char_count, "chunk_count": d.chunk_count, "created_at": d.created_at.isoformat(),
    }


@router.get("")
def list_documents(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    docs = db.query(models.Document).order_by(models.Document.created_at.desc()).all()
    return [_to_dict(d) for d in docs]


@router.post("/upload")
async def upload_document(file: UploadFile, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    filename = file.filename or "upload.txt"
    ext = os.path.splitext(filename)[1].lower()
    upload_dir = os.path.join(settings.data_dir, "uploaded_documents")
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{ext}")
    raw_bytes = await file.read()
    with open(saved_path, "wb") as f:
        f.write(raw_bytes)

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(saved_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = raw_bytes.decode("utf-8", errors="ignore")

    if not text.strip():
        raise HTTPException(422, "No extractable text found in the uploaded file.")

    doc = _index_document(db, filename, text, "auto", "upload", user.id)
    return _to_dict(doc)
