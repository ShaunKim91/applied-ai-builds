"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Lucent pairs this with a vector store (see vectorstore.py) that holds the
actual chunk text + embeddings — SQL rows here are the system of record for
documents and conversations, the vector store is the derived search index,
same "record + index" split used throughout this project series.
"""
import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # "user" | "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    """One document in the knowledge base — a seed corpus text or a user
    upload. `chunk_count` chunks of this document live in the vector store,
    each tagged with `document_id` metadata pointing back here."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(20), default="upload")  # "seed" | "upload"
    language: Mapped[str] = mapped_column(String(10), default="en")  # "en" | "ko"
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="New chat")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    """One turn in a chat session. For assistant turns, `citations_json`
    holds the retrieved sources shown alongside the answer, and the
    groundedness fields record ml/groundedness.py's verdict for that
    specific answer."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, default="")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    retrieval_mode: Mapped[str] = mapped_column(String(20), default="bi")  # "bi" | "bi+cross"
    provider: Mapped[str] = mapped_column(String(30), default="local")
    groundedness_score: Mapped[float] = mapped_column(Float, default=1.0)
    groundedness_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call is logged here — who, what model, how long,
    success/failure. Mirrors the pattern reused from the Week1-3 PoCs."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(255), default="anonymous")
    action: Mapped[str] = mapped_column(String(100))
    model_used: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="success")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
