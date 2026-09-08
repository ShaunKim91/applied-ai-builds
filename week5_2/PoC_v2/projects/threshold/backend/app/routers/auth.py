"""Auth endpoints — signup/login/refresh/logout/me.

Cookie-based session (see security.py's module docstring for the full
rationale): login/refresh set httpOnly access+refresh cookies plus a
readable csrf_token cookie; every other mutating endpoint in this app
requires that csrf_token be echoed back as an `X-CSRF-Token` header.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from .. import models, security
from ..config import settings
from ..database import get_db
from ..rate_limit import rate_limit_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_COOKIE_KWARGS = dict(httponly=True, secure=settings.cookie_secure, samesite="strict")


class SignupIn(BaseModel):
    email: str
    password: str
    display_name: str = ""

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def valid_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    response.set_cookie("access_token", access_token, max_age=settings.access_token_expire_minutes * 60, **_COOKIE_KWARGS)
    response.set_cookie(
        "refresh_token", refresh_token, max_age=settings.refresh_token_expire_days * 86400, path="/api/auth", **_COOKIE_KWARGS
    )
    csrf_token = security.generate_csrf_token()
    response.set_cookie(
        "csrf_token", csrf_token, max_age=settings.refresh_token_expire_days * 86400, secure=settings.cookie_secure, samesite="strict"
    )
    return csrf_token


def _user_dict(user: models.User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role, "org_id": user.org_id}


@router.post("/signup", dependencies=[Depends(rate_limit_auth)])
def signup(payload: SignupIn, response: Response, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "An account with this email already exists.")
    org = db.query(models.Organization).first()
    if not org:
        raise HTTPException(500, "No organization seeded — this shouldn't happen outside a broken bootstrap.")
    user = models.User(
        org_id=org.id,
        email=payload.email,
        hashed_password=security.hash_password(payload.password),
        display_name=payload.display_name or payload.email.split("@")[0],
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    access = security.create_access_token(user)
    refresh = security.issue_refresh_token(db, user)
    _set_session_cookies(response, access, refresh)
    return {"user": _user_dict(user)}


@router.post("/login", dependencies=[Depends(rate_limit_auth)])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(401, "Incorrect email or password.")
    if security.is_locked_out(user):
        raise HTTPException(423, f"Account locked due to repeated failed logins. Try again in a few minutes.")
    if not security.verify_password(payload.password, user.hashed_password):
        security.record_failed_login(db, user)
        raise HTTPException(401, "Incorrect email or password.")
    security.record_successful_login(db, user)
    access = security.create_access_token(user)
    refresh = security.issue_refresh_token(db, user)
    _set_session_cookies(response, access, refresh)
    return {"user": _user_dict(user)}


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(401, "No refresh token presented.")
    result = security.rotate_refresh_token(db, raw)
    if not result:
        raise HTTPException(401, "Refresh token is invalid, expired, or already used.")
    user, new_refresh = result
    access = security.create_access_token(user)
    _set_session_cookies(response, access, new_refresh)
    return {"user": _user_dict(user)}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if raw:
        row = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == security.hash_token(raw)).first()
        if row:
            import datetime as dt

            row.revoked_at = dt.datetime.utcnow()
            db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("csrf_token")
    return {"ok": True}


@router.get("/me")
def me(user: models.User = Depends(security.get_current_user)):
    return _user_dict(user)
