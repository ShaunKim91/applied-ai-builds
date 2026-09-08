"""SQL-backed conversation memory: a `BaseChatMessageHistory`-compatible
view over `ConversationTurn` rows, plus the dual-strategy window+summary
logic that directly closes a well-known gap in a typical first-pass
implementation of this pattern ("메모리 미영속화" / "memory not persisted,
lost on restart" — a self-documented "not yet done" extension in that kind
of baseline; this module is that extension, done, backed by the same
SQLite database every other table in this app already uses).

**A verified, deliberate deviation from the obvious "idiomatic LangChain"
choice, not an oversight**: `langchain_core.runnables.history
.RunnableWithMessageHistory` looks like the natural fit for "wrap an LCEL
chain with message history." Directly checked against the actual installed
`langchain-core==0.3.86` before writing this module: constructing one emits
`LangChainPendingDeprecationWarning: RunnableWithMessageHistory is
deprecated. Use LangGraph's built-in persistence instead.` Adopting
LangGraph's persistence model would pull in a package and a state-machine
architecture outside this project's own LangChain/LCEL scope (never
LangGraph) — a real scope-and-dependency cost for a component the library
itself already flags for removal. Instead, this module implements the same
job explicitly: `SQLCaseMessageHistory` still implements the real
`BaseChatMessageHistory` interface (so it is usable anywhere that
interface is expected, and is unit-testable in isolation), and
`chains/orchestrator.py` loads/windows/summarizes it directly around real
LCEL primitives (`ChatPromptTemplate` + `MessagesPlaceholder`,
`trim_messages`, `local_llm`) rather than through the deprecated wrapper.
"""
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from .. import models
from .llm_runnable import local_llm

SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You maintain a running case summary for a Fenwick Mutual contact-center case. "
        "Given the EXISTING summary (may be empty) and a batch of OLDER turns being folded out of the "
        "live window, produce an updated summary: 2-5 short bullet-style facts, no preamble, no repeated "
        "content already captured. Preserve concrete facts (names, policy numbers, dates, amounts) exactly; "
        "never invent a fact that isn't in the summary or the turns.",
    ),
    ("human", "Existing summary:\n{existing_summary}\n\nOlder turns to fold in:\n{turns_text}\n\nUpdated summary:"),
])
_summary_chain = SUMMARY_PROMPT | local_llm | StrOutputParser()


class SQLCaseMessageHistory(BaseChatMessageHistory):
    """A real `BaseChatMessageHistory` implementation backed by
    `ConversationTurn` rows for one case. `add_messages` exists for
    interface completeness and unit testing; the primary write path is
    `chains/orchestrator.py`, which writes `ConversationTurn` rows directly
    because it needs to also set `redacted`/`tool_name`, fields this base
    interface has no vocabulary for."""

    def __init__(self, db: Session, case_id: int):
        self.db = db
        self.case_id = case_id

    @property
    def messages(self) -> list[BaseMessage]:
        rows = (
            self.db.query(models.ConversationTurn)
            .filter(models.ConversationTurn.case_id == self.case_id)
            .order_by(models.ConversationTurn.id.asc())
            .all()
        )
        out: list[BaseMessage] = []
        for r in rows:
            if r.role == "human":
                out.append(HumanMessage(content=r.content))
            elif r.role == "ai":
                out.append(AIMessage(content=r.content))
        return out

    def add_messages(self, messages: list[BaseMessage]) -> None:
        for m in messages:
            role = "human" if isinstance(m, HumanMessage) else "ai"
            self.db.add(models.ConversationTurn(case_id=self.case_id, role=role, content=m.content))
        self.db.commit()

    def clear(self) -> None:
        self.db.query(models.ConversationTurn).filter(models.ConversationTurn.case_id == self.case_id).delete()
        self.db.commit()


def windowed_messages(db: Session, case_id: int, window_turns: int) -> list[BaseMessage]:
    """The verbatim half of the dual strategy — mirrors a common
    `history[-6:]` window-memory technique, expressed via the real LCEL
    `trim_messages` utility rather than a bare Python slice. `window_turns`
    is a turn *pair* count (human+ai), so the message budget is doubled."""
    history = SQLCaseMessageHistory(db, case_id).messages
    if not history:
        return []
    return trim_messages(history, max_tokens=window_turns * 2, token_counter=len, strategy="last", include_system=False)


def maybe_summarize(db: Session, case: models.CallerCase, window_turns: int) -> bool:
    """Called after each turn is persisted. If the case now has more turns
    than fit in the live window, folds the oldest overflowing turns into
    `case.case_summary` via `_summary_chain` and advances
    `summarized_through_turn_id` so they are never re-summarized. Returns
    True if a summarization actually ran (used by verify_e2e.py to assert
    the window->summary transition really happens, not just that the code
    path exists)."""
    rows = (
        db.query(models.ConversationTurn)
        .filter(models.ConversationTurn.case_id == case.id, models.ConversationTurn.id > case.summarized_through_turn_id)
        .order_by(models.ConversationTurn.id.asc())
        .all()
    )
    live_window_size = window_turns * 2
    overflow = rows[: max(0, len(rows) - live_window_size)]
    if not overflow:
        return False
    turns_text = "\n".join(f"{r.role}: {r.content}" for r in overflow)
    updated = _summary_chain.invoke({"existing_summary": case.case_summary or "(none yet)", "turns_text": turns_text})
    case.case_summary = updated.strip()
    case.summarized_through_turn_id = overflow[-1].id
    db.commit()
    return True
