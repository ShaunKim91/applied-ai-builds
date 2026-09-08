"""Audit-log writer used by every AI-calling endpoint, plus a small timing
context manager so latency is measured consistently.
"""
import time
from contextlib import contextmanager

from sqlalchemy.orm import Session

from . import models


def log_action(
    db: Session,
    user,
    action: str,
    model_used: str = "",
    detail: str = "",
    status: str = "success",
    latency_ms: float = 0.0,
) -> None:
    entry = models.AuditLog(
        user_id=getattr(user, "id", None),
        user_email=getattr(user, "email", "anonymous"),
        action=action,
        model_used=model_used,
        detail=(detail or "")[:2000],
        latency_ms=latency_ms,
        status=status,
    )
    db.add(entry)
    db.commit()


@contextmanager
def timed():
    """Usage: with timed() as elapsed: ...; ms = elapsed()"""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000
