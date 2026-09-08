"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Structurally multi-tenant-ready (an `Organization` row per customer, every
other table FK'd to `org_id`) — the same commercial-grade upgrade over a
hardcoded singleton `id=1` row that Verity (Week5_1's companion rebuild)
also uses, sharing the security/tenancy architecture without sharing any
actual code deployment.

Unlike every prior PoC's single "runner" concept, an AgentRun here can
legitimately pause mid-execution (`AWAITING_APPROVAL`) and later resume —
`messages_json` snapshots the full LLM conversation state needed to resume
exactly where it left off, potentially long after the original HTTP request
that started the run has ended.
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


class AgentRun(Base):
    """One ReAct agent execution, start to finish (which may span a real
    human approval delay in the middle). `messages_json` is the exact chat
    history handed to the local LLM so a paused run can be resumed with full
    fidelity — not just its trace summary, the actual conversation state."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text, default="")
    # RUNNING | AWAITING_APPROVAL | COMPLETED | BLOCKED_PERMISSION |
    # STOPPED_STEP_LIMIT | STOPPED_COST_CAP | HITL_DENIED | FAILED
    status: Mapped[str] = mapped_column(String(30), default="RUNNING")
    final_answer: Mapped[str] = mapped_column(Text, default="")
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    spent_cost: Mapped[int] = mapped_column(Integer, default=0)
    max_steps: Mapped[int] = mapped_column(Integer, default=6)
    cost_cap: Mapped[int] = mapped_column(Integer, default=150)
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    synth_mode: Mapped[str] = mapped_column(String(20), default="local")  # "local" | "openrouter"
    cloud_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    # onupdate (not just default) is load-bearing: the stale-run reaper
    # compares this against "now" to detect an abandoned in-flight run —
    # a real bug found and fixed in the old Cradle PoC (see debug/), applied
    # here from the start rather than reintroduced.
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentStep(Base):
    """One entry in a run's visible trace."""

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"))
    step_number: Mapped[int] = mapped_column(Integer, default=0)
    # thought_action | observation | final_answer | blocked | awaiting_approval | resumed
    kind: Mapped[str] = mapped_column(String(30), default="thought_action")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ApprovalRequest(Base):
    """A real Human-in-the-Loop gate — the one guardrail a typical
    first-pass build implements as a scaffolded feature but never wires
    into the shipped app. Threshold makes this a real, persisted,
    actionable, AMOUNT-AWARE queue — a genuine engineering upgrade over the
    old Cradle PoC's flat per-tool-name HITL gate (see guardrails.py)."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"))
    tool_name: Mapped[str] = mapped_column(String(60))
    tool_arg: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | denied
    reason: Mapped[str] = mapped_column(Text, default="")
    requested_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class GuardrailSetting(Base):
    """Org-scoped, admin-editable tool allowlist, step limit, cost cap, and
    the amount-aware payout approval threshold. Real, runtime-adjustable
    governance, not a hardcoded constant."""

    __tablename__ = "guardrail_settings"
    __table_args__ = (UniqueConstraint("org_id", name="uq_guardrail_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    allowed_tools_json: Mapped[str] = mapped_column(Text, default="[]")
    max_steps: Mapped[int] = mapped_column(Integer, default=6)
    cost_cap: Mapped[int] = mapped_column(Integer, default=150)
    payout_approval_threshold_usd: Mapped[float] = mapped_column(Float, default=2500.0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class BudgetSetting(Base):
    """Org-scoped daily OpenRouter spend cap for the opt-in model-routing
    escalation — same pattern validated in Verity."""

    __tablename__ = "budget_settings"
    __table_args__ = (UniqueConstraint("org_id", name="uq_budget_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=1.00)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call AND every tool-execution decision is logged
    here — who, what, how long (real, measured), success/failure — PLUS a
    hash chain (`prev_hash`/`entry_hash`) making the log tamper-evident,
    identical mechanism to Verity's own audit.py."""

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
