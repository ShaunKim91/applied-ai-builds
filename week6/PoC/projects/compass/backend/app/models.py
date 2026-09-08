"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Compass pairs this with a vector store (see vectorstore.py) that embeds
each past research report so the Archive page's semantic search works —
same "record + index" split used throughout this project series' PoCs. Unlike
Week4's Lucent (where the vector store held document chunks retrieved at
answer time), here the vector store holds Compass's OWN past output, since
this week's retrieval source is the live web, not a fixed local corpus.
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


class ResearchSession(Base):
    """A research thread — one or more queries the user refines over time,
    shown in the UI as a stream of 'dispatches' rather than chat bubbles."""

    __tablename__ = "research_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="New research")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ReportEntry(Base):
    """One research report within a session — the core unit of Compass.

    `mode` distinguishes an ordinary research dispatch from a Trend Radar
    run (same underlying search+synthesis pipeline, plus a structured
    cost/security/approval extraction stored in `radar_json`) — see
    routers/trend_radar.py. `search_mode` and `synth_mode` record which of
    the independently-selectable search backend and generation backend
    actually served this specific report (both can fail over independently;
    see search/web_search.py and ml/llm.py).
    """

    __tablename__ = "report_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: a Grounding Lab comparison run is a standalone scratchpad,
    # not part of any research thread, but still uses this same table so it
    # shares one unified cost ledger (see routers/research.py's
    # today_openrouter_spend) rather than needing a second accounting path.
    session_id: Mapped[int | None] = mapped_column(ForeignKey("research_sessions.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="research")  # "research" | "trend_radar" | "grounding_lab"
    query: Mapped[str] = mapped_column(Text, default="")
    report_text: Mapped[str] = mapped_column(Text, default="")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    ghost_citations_json: Mapped[str] = mapped_column(Text, default="[]")
    radar_json: Mapped[str] = mapped_column(Text, default="null")
    search_mode: Mapped[str] = mapped_column(String(20), default="ddgs")  # "ddgs" | "mock" | "openrouter_web"
    synth_mode: Mapped[str] = mapped_column(String(20), default="local")  # "local" | "openrouter"
    groundedness_score: Mapped[float] = mapped_column(Float, default=1.0)
    groundedness_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class BudgetSetting(Base):
    """Singleton row (id=1) holding the admin-configured daily spend cap —
    the "비용 상한" (budget cap) discipline, a standard cost-governance
    practice that a typical baseline implementation of this pattern never
    implements. See routers/admin.py's cost-governance endpoints and
    search/web_search.py's /ml/llm.py's use of it to force a free-path
    fallback once exceeded."""

    __tablename__ = "budget_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=1.00)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call is logged here — who, what model, how long,
    success/failure. Mirrors the pattern reused from the Week1-4 PoCs."""

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
