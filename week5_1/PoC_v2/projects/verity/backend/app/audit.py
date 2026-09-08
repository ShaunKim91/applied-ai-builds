"""A tamper-evident, hash-chained audit log.

Every earlier product in this series logged AI calls to a plain `audit_logs`
table — real data, but nothing stopped a row from being silently edited or
deleted after the fact. Here, each row also stores `entry_hash =
sha256(prev_hash || canonical_json(row_content))`, chaining it to the row
before it — the same structural idea a blockchain/git commit chain uses,
applied to an audit trail an insurance compliance team would actually need
to hand a regulator. `verify_chain()` walks the whole table and reports the
first row where the stored hash no longer matches what its own content
would produce — proof the log wasn't altered after being written, not just
an assertion that it wasn't.
"""
import hashlib
import json

from sqlalchemy.orm import Session

from . import models


def _canonical(row: dict) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def _compute_hash(prev_hash: str, content: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(content)).encode("utf-8")).hexdigest()


def _content_for_hash(entry: models.AuditLog) -> dict:
    return {
        "org_id": entry.org_id,
        "user_id": entry.user_id,
        "user_email": entry.user_email,
        "action": entry.action,
        "model_used": entry.model_used,
        "detail": entry.detail,
        "latency_ms": round(entry.latency_ms, 3),
        "status": entry.status,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def log_action(
    db: Session,
    user: models.User | None,
    action: str,
    *,
    org_id: int | None = None,
    model_used: str = "",
    detail: str = "",
    latency_ms: float = 0.0,
    status: str = "success",
) -> models.AuditLog:
    last = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).first()
    prev_hash = last.entry_hash if last else ""
    entry = models.AuditLog(
        org_id=org_id if org_id is not None else (user.org_id if user else 0),
        user_id=user.id if user else None,
        user_email=user.email if user else "anonymous",
        action=action,
        model_used=model_used,
        detail=detail,
        latency_ms=latency_ms,
        status=status,
        prev_hash=prev_hash,
    )
    # entry_hash needs entry.created_at, which default=utcnow() only fills
    # in at flush time — flush (not commit) first so the value exists before
    # we hash it, then set the hash and commit once.
    db.add(entry)
    db.flush()
    entry.entry_hash = _compute_hash(prev_hash, _content_for_hash(entry))
    db.commit()
    return entry


def verify_chain(db: Session) -> dict:
    """Walks every AuditLog row in id order and recomputes each hash from
    its own stored content + the previous row's stored hash. Returns
    {"intact": bool, "checked": int, "first_broken_id": int | None}."""
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
    prev_hash = ""
    for row in rows:
        expected = _compute_hash(prev_hash, _content_for_hash(row))
        if expected != row.entry_hash:
            return {"intact": False, "checked": len(rows), "first_broken_id": row.id}
        prev_hash = row.entry_hash
    return {"intact": True, "checked": len(rows), "first_broken_id": None}
