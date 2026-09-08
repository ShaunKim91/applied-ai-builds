"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Structurally multi-tenant-ready (an `Organization` row per customer, every
other table FK'd to `org_id`) even though this demo only ever seeds one —
Fenwick Mutual — rather than the singleton `id=1` rows every prior product
in this series used for its admin-editable settings. See architecture.md's
security section for why this is a deliberate "commercial-grade" upgrade,
not scope creep: a real second customer could be onboarded without a schema
migration, only a new `Organization` row.
"""
import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class Organization(Base):
    """A Fenwick-Mutual-shaped customer account. Exactly one row is seeded
    this round — the point isn't a working tenant-switcher UI (explicitly
    out of scope), it's that every other table already points at `org_id`
    instead of a hardcoded singleton, so adding a second real customer later
    is a data change, not a schema change."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Fictional jurisdiction codes this insurer is "licensed" in — see
    # search/jurisdictions.py. Deliberately fictional; see docs/guide.html's
    # non-overclaim disclaimer.
    licensed_jurisdictions_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # "user" | "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Account lockout — a real commercial-grade auth feature none of the
    # Week1-5_2 PoCs implemented. Reset to 0 on any successful login.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class RefreshToken(Base):
    """Supports access+refresh token rotation (security.py) — replacing
    every prior PoC's single flat 24h JWT with a short-lived access token
    plus a longer-lived, rotated, revocable refresh token. Only a SHA-256
    hash of the actual token is ever stored, mirroring how passwords are
    stored — a stolen DB row can't be replayed as a live session."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class CatEvent(Base):
    """A catastrophe/weather event as a first-class object — Dana pins a
    named event (a hailstorm, a wind event) and every research report tied
    to it rolls up underneath it. An object-model upgrade over the old
    Compass PoC's flat session list."""

    __tablename__ = "cat_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(40), default="other")  # hail|wind|flood|wildfire|other
    region: Mapped[str] = mapped_column(String(120), default="")  # a fictional jurisdiction/region
    occurred_on: Mapped[dt.date] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ResearchSession(Base):
    """One claim-research thread — the 'Claim Research Library' reframing of
    the old Compass Archive: tagged with a claim number, a fictional
    jurisdiction, and optionally a CatEvent, so the library can be filtered
    the way Dana's own job actually organizes work."""

    __tablename__ = "research_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(300), default="")
    claim_number: Mapped[str] = mapped_column(String(60), default="")
    jurisdiction: Mapped[str] = mapped_column(String(60), default="")
    cat_event_id: Mapped[int | None] = mapped_column(ForeignKey("cat_events.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ReportEntry(Base):
    """One AI-generated research turn. `mode` discriminates three genuinely
    different output shapes sharing one grounding pipeline (pipeline.py):
    a free-form 'quick answer', a structured 'precedent brief' (Issue /
    Governing Authority / Facts Applied / Recommendation / Sources), and a
    'radar' vendor/tool-adoption evaluation (the old Compass Trend Radar,
    reframed)."""

    __tablename__ = "report_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("research_sessions.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="quick")  # quick | precedent_brief | radar
    query: Mapped[str] = mapped_column(Text, default="")
    report_text: Mapped[str] = mapped_column(Text, default="")
    # Structured precedent-brief fields, populated only when mode=precedent_brief.
    brief_json: Mapped[str] = mapped_column(Text, default="{}")
    # Vendor/tool adoption verdict, populated only when mode=radar.
    radar_json: Mapped[str] = mapped_column(Text, default="{}")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    # Per-source trust tier: primary regulatory | secondary trade pub | unverified.
    source_trust_json: Mapped[str] = mapped_column(Text, default="[]")
    ghost_citations_json: Mapped[str] = mapped_column(Text, default="{}")
    # Matches against the fictional fraud-pattern taxonomy (ml/fraud_signals.py) —
    # always framed as "possible signal", never a determination.
    fraud_signals_json: Mapped[str] = mapped_column(Text, default="[]")
    groundedness_score: Mapped[float] = mapped_column(Float, default=0.0)
    jurisdiction: Mapped[str] = mapped_column(String(60), default="")
    claim_number: Mapped[str] = mapped_column(String(60), default="")
    search_mode: Mapped[str] = mapped_column(String(20), default="mock")  # ddgs | mock
    synth_mode: Mapped[str] = mapped_column(String(20), default="local")  # local | openrouter
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class BudgetSetting(Base):
    """Org-scoped daily OpenRouter spend cap — the same governance pattern
    validated in the old Compass/Cradle PoCs, now keyed by org_id instead of
    a hardcoded singleton id=1 row."""

    __tablename__ = "budget_settings"
    __table_args__ = (UniqueConstraint("org_id", name="uq_budget_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=1.00)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call is logged here — who, what, how long, real
    measured latency, success/failure — PLUS a hash chain
    (`prev_hash`/`entry_hash`) making the log tamper-evident: an admin's
    'Verify Integrity' action recomputes each row's hash from its own
    content and the previous row's hash, and any edited/deleted/reordered
    row breaks the chain at exactly that point. See audit.py."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(255), default="anonymous")
    action: Mapped[str] = mapped_column(String(100))
    model_used: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="success")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    entry_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ErrorLog(Base):
    """Structured, correlation-ID-tagged unhandled-exception record — a
    lightweight local stand-in for a real error-tracking service (Sentry-
    alike), surfaced on an admin 'Recent Errors' panel. The client response
    for the same error never includes the stack trace (see main.py's
    exception handler) — only this server-side row does."""

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(40), default="")
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    route: Mapped[str] = mapped_column(String(200), default="")
    method: Mapped[str] = mapped_column(String(10), default="")
    error_class: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
