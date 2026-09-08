"""Authentication: password hashing, JWT access tokens, rotating refresh
tokens, CSRF double-submit protection, and account lockout.

A deliberate commercial-grade upgrade over every prior PoC in this
project series, which all used one flat 24h JWT returned in the response body
and read from `localStorage` by the SPA. Here:

- Both the access token (short-lived, `access_token_expire_minutes`) and the
  refresh token (longer-lived, rotated on every use) live in httpOnly,
  Secure, SameSite=Strict cookies — never in JS-reachable storage, so a
  script-injection XSS can't exfiltrate a live session token.
- A separate, NON-httpOnly `csrf_token` cookie holds a random value the SPA
  must echo back in an `X-CSRF-Token` header on every state-changing
  request (the "double-submit cookie" pattern) — cookies alone would let a
  third-party site's form silently ride the user's session; requiring the
  header too means only same-origin JS (which can read its own cookies) can
  construct a valid mutating request.
- A refresh token is single-use: `POST /api/auth/refresh` revokes the
  presented one and issues a new one. Only its SHA-256 hash is ever stored,
  mirroring how passwords are stored — a stolen DB row can't be replayed.
- Repeated failed logins lock the *account* (not just rate-limit the IP —
  see rate_limit.py for that separate, complementary defense).
"""
import datetime as dt
import hashlib
import secrets

from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user: models.User) -> str:
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user.email, "uid": user.id, "org": user.org_id, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user: models.User) -> str:
    """Creates a new RefreshToken row and returns the RAW token (only ever
    returned once, to be set as a cookie — never persisted in plaintext)."""
    raw = secrets.token_urlsafe(48)
    row = models.RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=dt.datetime.utcnow() + dt.timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    db.commit()
    return raw


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[models.User, str] | None:
    """Validates a presented refresh token, revokes it, and issues a new
    one. Returns (user, new_raw_token) or None if invalid/expired/revoked/
    reused — a revoked-but-presented-again token is treated as a possible
    theft signal and simply rejected (a real production system would also
    want to revoke the whole token family; documented as a known
    simplification in architecture.md)."""
    token_hash = hash_token(raw_token)
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if not row or row.revoked_at is not None or row.expires_at < dt.datetime.utcnow():
        return None
    user = db.get(models.User, row.user_id)
    if not user or not user.is_active:
        return None
    row.revoked_at = dt.datetime.utcnow()
    db.commit()
    new_raw = issue_refresh_token(db, user)
    return user, new_raw


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def is_locked_out(user: models.User) -> bool:
    return bool(user.locked_until and user.locked_until > dt.datetime.utcnow())


def record_failed_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.max_failed_logins:
        user.locked_until = dt.datetime.utcnow() + dt.timedelta(minutes=settings.lockout_minutes)
    db.commit()


def record_successful_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    cred_error = HTTPException(401, "Not authenticated")
    if not access_token:
        raise cred_error
    try:
        payload = jwt.decode(access_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
    except JWTError:
        raise cred_error
    if not email:
        raise cred_error
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise cred_error
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def verify_csrf(request: Request, csrf_token: str | None = Cookie(default=None)) -> None:
    """Double-submit CSRF check for state-changing requests. Exempt routes
    (login/signup/refresh) are excluded at the router level, not here — this
    dependency is only wired into routes that already require a session."""
    header_token = request.headers.get("x-csrf-token")
    if not csrf_token or not header_token or not secrets.compare_digest(csrf_token, header_token):
        raise HTTPException(403, "CSRF token missing or invalid")
