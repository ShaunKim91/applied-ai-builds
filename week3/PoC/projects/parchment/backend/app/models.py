"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Parchment pairs this with a vector store (see vectorstore.py) used
specifically for near-duplicate document detection (a genuinely different
use case from full semantic search/RAG, which this project deliberately
leaves out of scope — see architecture.md for the scoping rationale).
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


class Receipt(Base):
    """One image-extraction request. Stores BOTH the classic-OCR path and
    the local-VLM path's results side by side, so the UI can show the
    "trained-CNN-concept vs. pretrained-multimodal-AI" comparison with
    real numbers rather than just narrating it."""

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="upload")  # "upload" | "sample"
    filename: Mapped[str] = mapped_column(String(255))
    image_path: Mapped[str] = mapped_column(String(500))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_structured_json: Mapped[str] = mapped_column(Text, default="")  # local-LLM-structured fields
    ocr_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    vlm_answer: Mapped[str] = mapped_column(Text, default="")
    vlm_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"), nullable=True)
    duplicate_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class PdfSummary(Base):
    """One PDF summarization request — records whether the scanned-PDF OCR
    fallback fired, and whether the numeric cross-check (every number the
    summary states must actually appear in the source text) passed."""

    __tablename__ = "pdf_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="upload")  # "upload" | "sample"
    filename: Mapped[str] = mapped_column(String(255))
    extracted_chars: Mapped[int] = mapped_column(Integer, default=0)
    used_scanned_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    chunks_summarized: Mapped[int] = mapped_column(Integer, default=0)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(30), default="local")
    numeric_check_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    numeric_check_detail: Mapped[str] = mapped_column(Text, default="")
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("pdf_summaries.id"), nullable=True)
    duplicate_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class HtmlScrape(Base):
    """One HTML-table-parsing request. Always local (no cloud engine option)
    — a deterministic parsing problem like this doesn't need an LLM."""

    __tablename__ = "html_scrapes"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_headers_json: Mapped[str] = mapped_column(Text, default="[]")
    preview_csv: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call is logged here — who, what model, how long,
    success/failure. Mirrors the "감사 추적 (audit trail)" pattern reused
    from the Week1/11 PoCs."""

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
