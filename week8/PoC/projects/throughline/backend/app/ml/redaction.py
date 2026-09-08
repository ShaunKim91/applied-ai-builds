"""Pattern-based PII redaction — applied at every point structured or
free-text conversation content crosses a trust boundary: before it is
persisted (`ConversationTurn.content`, `CallerCase.case_summary`,
`MemoryFact.field_value`), before it is sent to the OpenRouter escalation
path (the one moment content actually leaves this container), and before it
is rendered live in the Workspace UI's memory sidebar. One function, three
call sites (see chains/orchestrator.py) — not three separate
implementations that could drift apart.

**Explicit, honest scope** (see docs/guide.html "PII & retention scope" for
the full disclaimer; the same `[치환]`-style substitution idea this module
implements is a common introductory technique for PII handling): this is
regex pattern-matching against a
short list of common identifier *shapes* (SSN-like, phone-like, long
card-like digit runs, email addresses). It is NOT a certified PII-detection
engine, has no model behind it, and has known false negatives for anything
that doesn't match a fixed shape — a spoken name, a street address, an
account nickname. It is a real, verifiable, narrow control, not a
compliance guarantee.
"""
import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    # First digit, then 12-18 more digits each optionally preceded by a
    # separator — deliberately does NOT allow a trailing separator after the
    # final digit (an earlier `(?:\d[ -]?){13,19}` version did, and greedily
    # swallowed the space after a card number into the match, leaving
    # "[REDACTED_CARD]expires" with no space — caught by this module's own
    # smoke test, not shipped).
    ("CARD", re.compile(r"\b\d(?:[ -]?\d){12,18}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]


def redact(text: str) -> tuple[str, bool]:
    """Returns (redacted_text, was_redacted). Order matters — SSN and phone
    are checked before the broader CARD digit-run pattern so a phone number
    doesn't first get chewed up by the card matcher (a 10-digit phone number
    plus punctuation can otherwise overlap the 13-19-digit card window)."""
    if not text:
        return text, False
    out = text
    was_redacted = False
    for label, pattern in _PATTERNS:
        new_out, n = pattern.subn(f"[REDACTED_{label}]", out)
        if n:
            was_redacted = True
            out = new_out
    return out, was_redacted


def contains_pii(text: str) -> bool:
    return redact(text)[1]
