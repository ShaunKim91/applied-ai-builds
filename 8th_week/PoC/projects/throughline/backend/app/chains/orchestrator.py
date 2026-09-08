"""Ties the whole chain set together for one turn of a case:

  redact -> persist human turn -> extract structured facts (+ conflict
  guardrail) -> route (tool vs. direct reply) -> memory-conditioned
  auto-fill -> execute tool -> compose reply (streamed) -> redact -> persist
  AI turn -> maybe fold the window into the rolling summary.

Split into `prepare_turn()` (everything up to, but not including, the final
reply generation) and `finalize_turn()` (persist the reply + summarize)
specifically so `routers/workspace.py` can stream the reply live via SSE in
between the two — the same "prepare / stream / finalize" shape Threshold
uses for its ReAct loop, applied to a different mechanism (one routed
LCEL turn instead of a multi-step tool loop).
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action
from ..config import settings
from ..ml.redaction import redact
from . import extraction, router
from .llm_runnable import REPLY_SYSTEM_PROMPT, stream_reply
from .memory_store import maybe_summarize, windowed_messages
from .tools import TOOLS


def get_memory_settings(db: Session, org_id: int) -> models.MemorySetting:
    row = db.query(models.MemorySetting).filter(models.MemorySetting.org_id == org_id).first()
    if not row:
        row = models.MemorySetting(org_id=org_id, window_turns=settings.default_window_turns, redaction_enabled=settings.default_redaction_enabled)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


# Which MemoryFact field a given tool's argument can be auto-filled from
# when the router didn't supply (or the rep didn't state) a value — the
# mechanism-level pillar differentiator described in architecture.md: a
# tool call can draw on what earlier turns (possibly in an earlier case
# visit) already established, something Verity and Threshold structurally
# cannot do.
_AUTOFILL_MAP: dict[str, dict[str, str]] = {
    "lookup_caller_account": {"policy_number": "policy_number"},
    "check_callback_availability": {"preferred_window": "preferred_callback_window"},
}


@dataclass
class TurnContext:
    case_id: int
    router_result: router.RouterResult
    tool_name: str | None
    tool_result_text: str | None
    reply_messages: list
    # Plain dicts, NOT the live MemoryConflictLog ORM rows — see
    # debug/issue-01-... .md: `prepare_turn` and `finalize_turn` run against
    # TWO SEPARATE `SessionLocal()` sessions (the first is explicitly closed
    # in routers/cases.py's `finally: db.close()` before the SSE generator
    # even starts), so an ORM object created in the first session is
    # DETACHED by the time `finalize_turn` would touch its attributes —
    # exactly the session-lifetime pitfall Threshold's own
    # agent/orchestrator.py docstring already warns about, hit here in a
    # different spot despite that. Extracting plain field values here, while
    # the first session is still open, avoids it entirely.
    conflicts: list[dict]
    extraction_parsed: bool


def _autofill_args(db: Session, case_id: int, tool_name: str, tool_args: dict) -> dict:
    field_map = _AUTOFILL_MAP.get(tool_name, {})
    filled = dict(tool_args)
    for arg_name, fact_field in field_map.items():
        if filled.get(arg_name):
            continue
        fact = db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case_id, models.MemoryFact.field_name == fact_field).first()
        if fact:
            filled[arg_name] = fact.field_value
    return filled


def _facts_system_prompt(db: Session, case_id: int) -> str:
    """The structured "index card" (MemoryFact rows) is otherwise only a UI
    readout with no effect on the conversation itself — found via direct
    testing that a recall question ("what was the caller's name again?")
    asked outside the raw verbatim window had nothing to draw on, since only
    `windowed_messages()`'s transcript slice was ever fed to the reply
    chain. Injecting a compact facts block as part of the system prompt
    every turn is what actually makes persisted structured memory
    functional, not just visible — the real point of extracting it at all."""
    facts = db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case_id).all()
    if not facts:
        return REPLY_SYSTEM_PROMPT
    lines = [f"- {f.field_name}: {f.field_value}" for f in facts]
    return REPLY_SYSTEM_PROMPT + "\n\nKnown case facts so far (trust these over guessing):\n" + "\n".join(lines)


def prepare_turn(db: Session, case: models.CallerCase, user: models.User, message_text: str) -> TurnContext:
    from langchain_core.messages import HumanMessage, SystemMessage

    mset = get_memory_settings(db, user.org_id)
    redacted_text, was_redacted = redact(message_text) if mset.redaction_enabled else (message_text, False)

    human_turn = models.ConversationTurn(case_id=case.id, role="human", content=redacted_text, redacted=was_redacted)
    db.add(human_turn)
    db.commit()
    db.refresh(human_turn)

    extraction_result = extraction.extract(redacted_text)
    conflicts: list[models.MemoryConflictLog] = []
    if extraction_result.parsed and extraction_result.facts is not None:
        conflicts = extraction.apply_extracted_facts(db, case.id, human_turn.id, redacted_text, extraction_result.facts)

    router_result = router.route(redacted_text)
    tool_name: str | None = None
    tool_result_text: str | None = None
    combined_content = redacted_text

    if router_result.decision.action == "tool" and router_result.decision.tool_name in TOOLS:
        tool_name = router_result.decision.tool_name
        filled_args = _autofill_args(db, case.id, tool_name, router_result.decision.tool_args)
        try:
            tool_result_text = TOOLS[tool_name](**filled_args)
        except TypeError as exc:
            tool_result_text = f"Tool result: Error - missing or invalid arguments for {tool_name} ({exc})."
        db.add(models.ConversationTurn(case_id=case.id, role="tool", tool_name=tool_name, content=tool_result_text))
        db.commit()
        combined_content = f"{redacted_text}\n{tool_result_text}"

    history = windowed_messages(db, case.id, mset.window_turns)
    system_prompt = _facts_system_prompt(db, case.id)
    reply_messages = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=combined_content)]

    # Extract plain values from the conflict rows NOW, while this function's
    # session is still open — see TurnContext's own docstring comment for
    # why the ORM rows themselves must not cross into finalize_turn().
    conflict_dicts = [{"field_name": c.field_name, "resolution": c.resolution} for c in conflicts]

    return TurnContext(
        case_id=case.id,
        router_result=router_result,
        tool_name=tool_name,
        tool_result_text=tool_result_text,
        reply_messages=reply_messages,
        conflicts=conflict_dicts,
        extraction_parsed=extraction_result.parsed,
    )


def stream_turn_reply(ctx: TurnContext):
    """Thin pass-through kept as its own function so routers/workspace.py
    never has to reach into chains.llm_runnable directly."""
    yield from stream_reply(ctx.reply_messages)


def finalize_turn(db: Session, ctx: TurnContext, user: models.User, reply_text: str, latency_ms: float) -> models.ConversationTurn:
    mset = get_memory_settings(db, user.org_id)
    redacted_reply, _ = redact(reply_text) if mset.redaction_enabled else (reply_text, False)

    ai_turn = models.ConversationTurn(case_id=ctx.case_id, role="ai", content=redacted_reply)
    db.add(ai_turn)
    db.commit()
    db.refresh(ai_turn)

    # Re-fetched in THIS session, not the (already-closed) one prepare_turn
    # used — see TurnContext's docstring comment.
    case = db.get(models.CallerCase, ctx.case_id)
    maybe_summarize(db, case, mset.window_turns)

    router_detail = f"action={ctx.router_result.decision.action} tool={ctx.tool_name} attempts={ctx.router_result.attempts} fell_back={ctx.router_result.fell_back}"
    log_action(db, user, "case.turn", org_id=user.org_id, model_used=settings.local_chat_model, detail=router_detail, latency_ms=latency_ms)

    for conflict in ctx.conflicts:
        log_action(
            db,
            user,
            "memory.conflict" if conflict["resolution"] == "pending_confirmation" else "memory.overwrite",
            org_id=user.org_id,
            detail=f"field={conflict['field_name']} resolution={conflict['resolution']} case_id={ctx.case_id}",
        )

    return ai_turn


def purge_case(db: Session, case: models.CallerCase, requested_by: models.User) -> models.RetentionRequest:
    """A real hard-delete cascade, not a soft "archived" flag. Deliberately
    does NOT record the purged content anywhere — only that a purge
    happened, of what (title snapshot only), by whom, when. See
    ml/redaction.py's and this project's docs/guide.html's explicit,
    honest boundary: this deletes THIS application's own rows and records
    an audit entry; it cannot retract anything already sent to the
    OpenRouter escalation path during the case's lifetime."""
    from .. import vectorstore

    turns_deleted = db.query(models.ConversationTurn).filter(models.ConversationTurn.case_id == case.id).count()
    facts_deleted = db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case.id).count()

    db.query(models.ConversationTurn).filter(models.ConversationTurn.case_id == case.id).delete()
    db.query(models.MemoryFact).filter(models.MemoryFact.case_id == case.id).delete()
    db.query(models.MemoryConflictLog).filter(models.MemoryConflictLog.case_id == case.id).delete()

    retention = models.RetentionRequest(
        org_id=case.org_id,
        case_id=case.id,
        case_title_snapshot=case.title,
        requested_by_id=requested_by.id,
        turns_deleted=turns_deleted,
        facts_deleted=facts_deleted,
    )
    db.add(retention)

    vectorstore.delete(f"case-{case.id}")
    db.delete(case)
    db.commit()
    db.refresh(retention)

    log_action(db, requested_by, "case.purge", org_id=requested_by.org_id, detail=f"case_id={case.id} turns={turns_deleted} facts={facts_deleted}")
    return retention
