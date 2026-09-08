from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..ml import llm as llm_ml
from ..ml import sandbox as sandbox_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

SYSTEM_PROMPT = (
    "You are a data analyst. You are given a natural-language analysis request "
    "and a `data` variable already available in your Python execution environment: "
    'a list of DICTS, each shaped {"filename": str, "transcript": str, '
    '"language": str, "word_count": int}. `data` is NOT a list of tuples — always '
    "access fields by key, e.g. `record['word_count']`, never by unpacking "
    "positions like `for a, b, c in data`. Example of the correct pattern: "
    "`total = sum(r['word_count'] for r in data) / len(data)`. Write ONLY a short "
    "Python code snippet (no explanation, no markdown fences, no imports) that "
    "computes the answer and prints it with print(). Keep it under 15 lines. Only "
    "use these builtins: len, range, print, sum, min, max, sorted, abs, round, "
    "enumerate, zip, list, dict, set, tuple, str, int, float, bool, isinstance, "
    "type, map, filter, any, all, reversed. No imports, no file or network access "
    "— they are not available."
)


class AnalyzeRequest(BaseModel):
    request_text: str = Field(..., min_length=3, max_length=300)
    use_openrouter: bool = False


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _meeting_dataset(db: Session) -> list[dict]:
    meetings = db.query(models.Meeting).all()
    return [
        {
            "filename": m.filename,
            "transcript": m.transcript,
            "language": m.detected_language,
            "word_count": len(m.transcript.split()) if m.transcript else 0,
        }
        for m in meetings
    ]


@router.post("/analyze")
def analyze(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    provider = "openrouter" if payload.use_openrouter else "local"
    data = _meeting_dataset(db)

    record = models.SandboxRun(
        owner_id=user.id, request_text=payload.request_text, provider=provider, status="running"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        with timed() as elapsed:
            gen = llm_ml.generate(SYSTEM_PROMPT, payload.request_text, provider=provider, max_new_tokens=220)
            code = _strip_code_fences(gen["text"])
            result = sandbox_ml.run_code(code, data)
        latency = elapsed()

        record.generated_code = code
        record.stdout = result["stdout"]
        record.stderr = result["stderr"]
        record.status = "failed" if result["exit_code"] != 0 else "done"
        record.duration_seconds = latency / 1000
        db.commit()

        model_used = settings.openrouter_model if provider == "openrouter" else settings.local_llm_model
        log_action(
            db, user, "sandbox.analyze", model_used=model_used,
            detail=payload.request_text, latency_ms=latency, status=record.status,
        )

        return {
            "id": record.id,
            "generated_code": code,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
            "timed_out": result["timed_out"],
            "provider": provider,
        }
    except Exception as exc:
        record.status = "failed"
        record.stderr = str(exc)
        db.commit()
        raise HTTPException(500, f"Analysis failed: {exc}")


@router.get("/runs")
def recent_runs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    runs = db.query(models.SandboxRun).order_by(models.SandboxRun.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "request_text": r.request_text,
            "provider": r.provider,
            "status": r.status,
            "generated_code": r.generated_code,
            "stdout": r.stdout,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
