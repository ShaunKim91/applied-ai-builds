"""SQLAlchemy ORM models — the relational (SQL) storage layer.

Cradle pairs this with a vector store (see vectorstore.py) that embeds each
finished agent run (question + final answer) so the History page's semantic
search works — same "record + index" split used throughout this project series'
PoCs. Unlike every prior PoC's single "runner" concept, an AgentRun here can
legitimately pause mid-execution (`AWAITING_APPROVAL`) and later resume —
`messages_json` snapshots the full LLM conversation state needed to resume
exactly where it left off, potentially long after the original HTTP request
that started the run has ended.
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


class AgentRun(Base):
    """One ReAct agent execution, start to finish (which may span a real
    human approval delay in the middle). `messages_json` is the exact chat
    history handed to the local LLM so a paused run can be resumed with full
    fidelity — not just its trace summary, the actual conversation state."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text, default="")
    # RUNNING | AWAITING_APPROVAL | COMPLETED | BLOCKED_PERMISSION |
    # STOPPED_STEP_LIMIT | STOPPED_COST_CAP | HITL_DENIED | FAILED
    status: Mapped[str] = mapped_column(String(30), default="RUNNING")
    final_answer: Mapped[str] = mapped_column(Text, default="")
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    spent_cost: Mapped[int] = mapped_column(Integer, default=0)
    max_steps: Mapped[int] = mapped_column(Integer, default=5)
    cost_cap: Mapped[int] = mapped_column(Integer, default=100)
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    synth_mode: Mapped[str] = mapped_column(String(20), default="local")  # "local" | "openrouter"
    # Set only if this run was escalated to OpenRouter (see routers/agent.py's
    # /escalate) — real per-call cost is not returned by the API, so this
    # records the same documented ESTIMATE pattern Week6's Compass PoC
    # uses for its own OpenRouter cost ledger, never a fabricated number.
    cloud_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    # onupdate (not just default) is load-bearing: routers/agent.py's
    # stale-run reaper compares this against "now" to detect an abandoned
    # in-flight run, which only works if every real progress update to a
    # row actually bumps it — a plain `default=` alone only stamps the row
    # once at creation.
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentStep(Base):
    """One entry in a run's visible trace — rendered by the frontend as the
    layered 3D card stack. `kind` drives which depth/color treatment a step
    gets in the UI."""

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"))
    step_number: Mapped[int] = mapped_column(Integer, default=0)
    # thought_action | observation | final_answer | blocked | awaiting_approval | resumed
    kind: Mapped[str] = mapped_column(String(30), default="thought_action")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class ApprovalRequest(Base):
    """A real Human-in-the-Loop gate — the one guardrail a typical baseline
    implementation builds as a class feature but never wires into its
    shipped app (`approval_required_tools` stays an empty set). Cradle
    makes this a real, persisted, actionable queue."""

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
    """Singleton row (id=1) — admin-editable tool allowlist, step limit, and
    cost cap. Real, runtime-adjustable governance, not a hardcoded constant."""

    __tablename__ = "guardrail_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    allowed_tools_json: Mapped[str] = mapped_column(Text, default="[]")
    max_steps: Mapped[int] = mapped_column(Integer, default=5)
    cost_cap: Mapped[int] = mapped_column(Integer, default=100)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class BudgetSetting(Base):
    """Singleton row (id=1) holding the daily OpenRouter spend cap for the
    opt-in model-routing escalation — same pattern validated in the
    Week6 "Compass" PoC, reused here for a well-documented "model
    routing" trend instead of a web-search feature."""

    __tablename__ = "budget_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=1.00)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Every AI inference call AND every tool-execution decision is logged
    here — who, what, how long, success/failure. Mirrors the pattern reused
    from the Week1-6 PoCs."""

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
