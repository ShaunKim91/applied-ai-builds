"""Multi-turn RAG chat with real token-by-token streaming — the flagship
feature this week's brief calls for over the plain request/response
generation used throughout the Week1-3 PoCs.

Streamed as Server-Sent-Events-shaped lines over a POST request (a plain
GET-only `EventSource` can't carry a request body, so the frontend consumes
this with `fetch()` + a `ReadableStream` reader instead — see
frontend/src/pages/Chat.tsx).
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action
from ..config import settings
from ..database import SessionLocal, get_db
from ..ml import groundedness, llm
from ..rag import RAG_SYSTEM_PROMPT, build_context_block, retrieve
from ..security import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.owner_id == user.id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]


@router.post("/sessions")
def create_session(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = models.ChatSession(owner_id=user.id, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "created_at": session.created_at.isoformat()}


def _message_dict(m: models.ChatMessage) -> dict:
    # Shaped to match the *same* `groundedness: {passed, content_check: {score}}`
    # nested object the streaming 'done' SSE event sends (see send_message
    # below) — the frontend's Message type expects that one shape whether a
    # message arrives live via the stream or is reloaded via this endpoint.
    # Originally this returned flat groundedness_score/groundedness_passed
    # keys instead, which silently matched nothing in the frontend's type —
    # the grounded/partially-grounded badge rendered correctly right after a
    # live send, then disappeared the moment a session's history was
    # reloaded (revisit, refresh). citation_check detail isn't persisted
    # per-message, so it's omitted here; the badge only reads `passed` and
    # `content_check.score`, both of which are.
    groundedness = (
        {"passed": m.groundedness_passed, "content_check": {"score": m.groundedness_score}}
        if m.role == "assistant"
        else None
    )
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "citations": json.loads(m.citations_json),
        "retrieval_mode": m.retrieval_mode,
        "provider": m.provider,
        "groundedness": groundedness,
        "latency_ms": m.latency_ms,
        "created_at": m.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = db.get(models.ChatSession, session_id)
    if not session or session.owner_id != user.id:
        raise HTTPException(404, "Session not found")
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    return [_message_dict(m) for m in messages]


class SendMessageRequest(BaseModel):
    content: str
    use_rerank: bool = False
    use_openrouter: bool = False


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    session = db.get(models.ChatSession, session_id)
    if not session or session.owner_id != user.id:
        raise HTTPException(404, "Session not found")

    user_msg = models.ChatMessage(session_id=session_id, role="user", content=payload.content)
    db.add(user_msg)
    if session.title == "New chat":
        session.title = payload.content[:60]
    db.commit()

    provider = "openrouter" if payload.use_openrouter else "local"
    retrieval_mode = "bi+cross" if payload.use_rerank else "bi"
    start = time.perf_counter()
    sources = retrieve(payload.content, use_rerank=payload.use_rerank)
    context_block = build_context_block(sources)
    user_prompt = f"Sources:\n{context_block}\n\nQuestion: {payload.content}" if sources else payload.content

    def event_stream():
        full_text = []
        try:
            for fragment in llm.stream_generate(RAG_SYSTEM_PROMPT, user_prompt, provider=provider):
                full_text.append(fragment)
                yield f"data: {json.dumps({'delta': fragment})}\n\n"
        except Exception as exc:  # noqa: BLE001 — stream errors must reach the client, not vanish server-side
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return

        answer = "".join(full_text).strip()
        latency_ms = (time.perf_counter() - start) * 1000
        source_texts = [s["text"] for s in sources]
        verdict = groundedness.verify(answer, source_texts)

        db2 = SessionLocal()
        try:
            assistant_msg = models.ChatMessage(
                session_id=session_id,
                role="assistant",
                content=answer,
                citations_json=json.dumps(sources),
                retrieval_mode=retrieval_mode,
                provider=provider,
                groundedness_score=verdict["content_check"]["score"],
                groundedness_passed=verdict["passed"],
                latency_ms=latency_ms,
            )
            db2.add(assistant_msg)
            db2.commit()
            db2.refresh(assistant_msg)
            log_action(
                db2, user, "chat.message",
                model_used=settings.local_llm_model if provider == "local" else settings.openrouter_model,
                detail=f"retrieval={retrieval_mode}", latency_ms=latency_ms,
            )
            message_id = assistant_msg.id
        finally:
            db2.close()

        yield f"data: {json.dumps({'done': True, 'message_id': message_id, 'citations': sources, 'groundedness': verdict})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
