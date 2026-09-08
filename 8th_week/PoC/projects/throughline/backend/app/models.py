"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Structurally multi-tenant-ready (an `Organization` row per customer, every
other table FK'd to `org_id`) — the same commercial-grade upgrade over a
hardcoded singleton `id=1` row that Verity and Threshold both use, sharing
the security/tenancy architecture without sharing any actual code
deployment.

Unlike Verity's `ResearchSession`/`ReportEntry` or Threshold's
`AgentRun`/`AgentStep`, the center of gravity here is `CallerCase`: a
long-lived thread that can span many separate visits to the app (a
policyholder calling back next week is still "the same case"). Two tables
exist specifically to make that memory trustworthy rather than just
convenient: `MemoryFact` (the structured, LLM-extracted "index card" of what
we know about this case) and `MemoryConflictLog` (an audit trail of every
time a new extraction would have silently overwritten an already-confident
fact — Throughline's own guardrail axis, structurally analogous to how
Threshold gates a payout, applied instead to gating a *memory write*).
"""
import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
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
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class RefreshToken(Base):
    """Only a SHA-256 hash of the actual token is ever stored — a stolen DB
    row can't be replayed as a live session."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class CallerCase(Base):
    """One policyholder contact thread — the unit of conversational
    continuity. A rep opens a case at the start of a call (or reopens an
    existing one if the caller has phoned before about the same policy) and
    every turn, extracted fact, and tool call is scoped to it. `case_summary`
    is the rolling-summary half of the dual-strategy memory (see
    chains/memory_store.py): once the verbatim window (`window_turns`,
    org-configurable) overflows, the oldest turns are folded in here by a
    dedicated LCEL summarization chain rather than simply dropped."""

    __tablename__ = "caller_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | closed
    case_summary: Mapped[str] = mapped_column(Text, default="")
    summarized_through_turn_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConversationTurn(Base):
    """One message in a case's transcript. `content` has already passed
    through the redaction boundary (ml/redaction.py) before it is ever
    written here — this table is downstream of that boundary, not upstream
    of it, by construction (see chains/orchestrator.py)."""

    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("caller_cases.id"))
    role: Mapped[str] = mapped_column(String(20))  # human | ai | tool
    content: Mapped[str] = mapped_column(Text, default="")
    redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_name: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class MemoryFact(Base):
    """The live "index card" for one case: one row per distinct field.
    Overwriting an already-`confirmed` fact with a new, lower-confidence
    extraction never happens silently — see chains/extraction.py's conflict
    check, which routes a disagreement to `MemoryConflictLog` instead."""

    __tablename__ = "memory_facts"
    __table_args__ = (UniqueConstraint("case_id", "field_name", name="uq_memory_fact_case_field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("caller_cases.id"))
    field_name: Mapped[str] = mapped_column(String(60))  # caller_name | policy_number | preferred_callback_window | topic
    field_value: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(20), default="stated")  # stated | inferred
    source_turn_id: Mapped[int | None] = mapped_column(ForeignKey("conversation_turns.id"), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MemoryConflictLog(Base):
    """An audit trail of every time structured extraction proposed
    overwriting an existing `MemoryFact` with a materially different value.
    This IS Throughline's guardrail layer — not a payout gate (it has no
    payout-capable tools; that risk belongs to Threshold), but a memory-
    integrity gate: silently corrupting "what we remember about this caller"
    is the structural analog of a wrong payout for a memory-centric product."""

    __tablename__ = "memory_conflict_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("caller_cases.id"))
    field_name: Mapped[str] = mapped_column(String(60))
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str] = mapped_column(String(30), default="pending_confirmation")  # pending_confirmation | kept_old | accepted_new
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class RetentionRequest(Base):
    """A record that a case's data was purged — deliberately does NOT store
    the purged content, only that a purge happened, of what, by whom, when.
    See ml/redaction.py's module docstring and docs/guide.html's "PII &
    retention scope" section for the explicit, honest boundary this feature
    claims (pattern-based redaction + a real hard-delete cascade — not a
    certified compliance program)."""

    __tablename__ = "retention_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    case_id: Mapped[int] = mapped_column(Integer)  # not a FK: the case row is gone by the time this is read back
    case_title_snapshot: Mapped[str] = mapped_column(String(200), default="")
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    turns_deleted: Mapped[int] = mapped_column(Integer, default=0)
    facts_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class MemorySetting(Base):
    """Org-scoped, admin-editable memory governance: the verbatim window
    size before summarization kicks in, and whether the redaction pass is
    enabled. Real, runtime-adjustable, not a hardcoded constant."""

    __tablename__ = "memory_settings"
    __table_args__ = (UniqueConstraint("org_id", name="uq_memory_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    window_turns: Mapped[int] = mapped_column(Integer, default=8)
    redaction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class BudgetSetting(Base):
    """Org-scoped daily OpenRouter spend cap for the opt-in model-routing
    escalation — same pattern validated in Verity and Threshold."""

    __tablename__ = "budget_settings"
    __table_args__ = (UniqueConstraint("org_id", name="uq_budget_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=1.00)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call, tool execution, and memory-write decision is
    logged here — who, what, how long (real, measured), success/failure —
    PLUS a hash chain (`prev_hash`/`entry_hash`) making the log
    tamper-evident, identical mechanism to Verity's and Threshold's own
    audit.py."""

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
    """Structured, correlation-ID-tagged unhandled-exception record."""

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
