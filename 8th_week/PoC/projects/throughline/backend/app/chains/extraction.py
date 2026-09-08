"""Structured memory-fact extraction — after each representative-authored
turn, a small LCEL-style call asks the local model what new facts (caller
name, policy number, a stated callback preference, the turn's topic) that
one message states, as JSON validated against `ExtractedFacts`. This is
Throughline's "index card": a live, structured summary of a case, distinct
from the free-text rolling `case_summary` in chains/memory_store.py.

**Grounding check, echoing Verity's own `ghost_citation.py` technique
across the suite**: an extracted value is only trusted as `confidence=
"stated"` if it actually appears (case-insensitively) in the turn text it
was extracted from — the same "does this claim actually appear in the
source" check Verity runs on research citations, applied here to memory
extraction instead of retrieved documents. A value the model produced that
is NOT found in the source turn is tagged `confidence="inferred"` and is
never allowed to silently overwrite an existing `stated` fact.

**The conflict guardrail** (this project's own answer to "does this
pillar need a safety mechanism," see architecture.md §4): overwriting an
existing `stated` `MemoryFact` with a different `stated` value is never
silent — it is logged as a `MemoryConflictLog` row in `pending_confirmation`
and the OLD value is kept until a person resolves it (`resolve_conflict`).
Every other overwrite path (a higher-confidence value replacing a lower one,
or vice versa being correctly refused) is still logged, just pre-resolved —
this project's version of "log every guardrail decision," applied to memory
writes instead of tool calls.
"""
import json
from dataclasses import dataclass
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from .. import models
from ..ml.redaction import redact
from .llm_runnable import local_llm

# Real LCEL composition, same shape as chains/router.py's `_route_chain` —
# see that module's comment for why validation/retry stays as explicit
# Python control flow rather than being folded into the pipe itself.
_extract_chain = local_llm | StrOutputParser()

EXTRACTION_SYSTEM_PROMPT = """Extract facts EXPLICITLY stated in the representative's message below — never infer or guess. Respond with ONLY a single JSON object, no other text:
{"caller_name": string or null, "policy_number": string or null, "preferred_callback_window": string or null, "topic": a short 2-4 word label for what this message is about, or null}

Only fill a field if the message actually states it. Leave every other field null. Do not repeat information from earlier turns unless this message restates it.

Example:
Message: "This is Diane Castellano calling about policy FM-100234, I'd prefer afternoon callbacks."
{"caller_name": "Diane Castellano", "policy_number": "FM-100234", "preferred_callback_window": "afternoon", "topic": "callback preference"}

Example:
Message: "Can you check my next payment date?"
{"caller_name": null, "policy_number": null, "preferred_callback_window": null, "topic": "payment date inquiry"}
"""

_FIELD_NAMES = ["caller_name", "policy_number", "preferred_callback_window", "topic"]


class ExtractedFacts(BaseModel):
    caller_name: Optional[str] = None
    policy_number: Optional[str] = None
    preferred_callback_window: Optional[str] = None
    topic: Optional[str] = None


@dataclass
class ExtractionResult:
    facts: ExtractedFacts | None
    parsed: bool


def extract(turn_text: str) -> ExtractionResult:
    messages = [SystemMessage(content=EXTRACTION_SYSTEM_PROMPT), HumanMessage(content=f'Message: "{turn_text}"')]
    raw = _extract_chain.invoke(messages)
    try:
        data = json.loads(raw)
        facts = ExtractedFacts.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return ExtractionResult(facts=None, parsed=False)
    return ExtractionResult(facts=facts, parsed=True)


def _confidence_for(value: str, source_text: str) -> str:
    return "stated" if value.lower() in source_text.lower() else "inferred"


def apply_extracted_facts(
    db: Session, case_id: int, source_turn_id: int, source_text: str, facts: ExtractedFacts
) -> list[models.MemoryConflictLog]:
    """Writes/updates `MemoryFact` rows for every non-null field in `facts`,
    applying the conflict guardrail described in this module's docstring.
    Returns any newly-created `MemoryConflictLog` rows (both auto-resolved
    and pending) so the caller (chains/orchestrator.py) can audit-log them."""
    conflicts: list[models.MemoryConflictLog] = []
    for field_name in _FIELD_NAMES:
        raw_value = getattr(facts, field_name)
        if not raw_value:
            continue
        value, _ = redact(raw_value.strip())
        if not value:
            continue
        confidence = _confidence_for(value, source_text)

        existing = (
            db.query(models.MemoryFact)
            .filter(models.MemoryFact.case_id == case_id, models.MemoryFact.field_name == field_name)
            .first()
        )
        if existing is None:
            db.add(
                models.MemoryFact(
                    case_id=case_id, field_name=field_name, field_value=value, confidence=confidence, source_turn_id=source_turn_id
                )
            )
            continue
        if existing.field_value == value:
            continue  # same value restated -- not a conflict, no-op

        if existing.confidence == "stated" and confidence == "stated":
            conflict = models.MemoryConflictLog(
                case_id=case_id, field_name=field_name, old_value=existing.field_value, new_value=value, resolution="pending_confirmation"
            )
            db.add(conflict)
            conflicts.append(conflict)
            # existing value is kept as-is until a human resolves this
        elif existing.confidence == "stated" and confidence == "inferred":
            conflict = models.MemoryConflictLog(
                case_id=case_id, field_name=field_name, old_value=existing.field_value, new_value=value, resolution="kept_old"
            )
            db.add(conflict)
            conflicts.append(conflict)
        else:
            # existing is "inferred" -- a "stated" or equally "inferred" new
            # value is allowed to replace it, but the overwrite is still
            # logged (never silent), per this module's own stated principle.
            conflict = models.MemoryConflictLog(
                case_id=case_id, field_name=field_name, old_value=existing.field_value, new_value=value, resolution="accepted_new"
            )
            db.add(conflict)
            conflicts.append(conflict)
            existing.field_value = value
            existing.confidence = confidence
            existing.source_turn_id = source_turn_id
    db.commit()
    return conflicts


def resolve_conflict(db: Session, conflict_id: int, resolution: str, resolved_by_id: int) -> models.MemoryConflictLog | None:
    """A human resolving a `pending_confirmation` row from the Workspace UI:
    `resolution` is "accepted_new" (overwrite the fact) or "kept_old" (leave
    it alone). Both outcomes are recorded on the SAME row (not a new one) so
    the audit trail shows exactly what was pending and how it was settled."""
    import datetime as dt

    conflict = db.get(models.MemoryConflictLog, conflict_id)
    if conflict is None or conflict.resolution != "pending_confirmation":
        return None
    if resolution == "accepted_new":
        fact = (
            db.query(models.MemoryFact)
            .filter(models.MemoryFact.case_id == conflict.case_id, models.MemoryFact.field_name == conflict.field_name)
            .first()
        )
        if fact:
            fact.field_value = conflict.new_value
            fact.confidence = "stated"
    conflict.resolution = resolution
    conflict.resolved_by_id = resolved_by_id
    conflict.resolved_at = dt.datetime.utcnow()
    db.commit()
    return conflict
