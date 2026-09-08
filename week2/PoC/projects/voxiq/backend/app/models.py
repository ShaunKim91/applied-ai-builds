"""SQLAlchemy ORM models — the relational (SQL) storage layer.

VoxIQ pairs this with a vector store (see vectorstore.py) so both
"structured DB" and "Vector DB" storage patterns are demonstrated, matching
real enterprise knowledge-platform architectures.
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


class Meeting(Base):
    """A transcribed audio recording — the "meeting record" this platform
    indexes and searches over."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="upload")  # "upload" | "sample"
    filename: Mapped[str] = mapped_column(String(255))
    audio_path: Mapped[str] = mapped_column(String(500))
    transcript: Mapped[str] = mapped_column(Text, default="")
    detected_language: Mapped[str] = mapped_column(String(20), default="")
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    transcribe_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class SearchQuery(Base):
    """One knowledge-search request — stores both the bi-encoder-only
    ranking and the cross-encoder-reranked ranking so the UI can show the
    "before vs after reranking" comparison directly."""

    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text)
    bi_results_json: Mapped[str] = mapped_column(Text)  # JSON list, bi-encoder order
    cross_results_json: Mapped[str] = mapped_column(Text)  # JSON list, cross-encoder order
    top1_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class SandboxRun(Base):
    """One Analytics Agent request: a natural-language question, the code
    an LLM generated for it, and the isolated sandbox's real output."""

    __tablename__ = "sandbox_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    request_text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(30), default="local")
    generated_code: Mapped[str] = mapped_column(Text, default="")
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|done|failed
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call is logged here — who, what model, how long,
    success/failure. Mirrors the "감사 추적 (audit trail)" pattern common in
    agentic-AI system design, applied consistently across this project
    series' products."""

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
