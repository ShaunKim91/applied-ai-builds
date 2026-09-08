import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = 60 * 60 * 24  # 24h, matches settings.jwt_expire_minutes default

# A deliberately loose email *shape* check (local-part@domain, domain has a
# dot). We intentionally do NOT use pydantic's EmailStr here — its
# `email-validator` backend rejects reserved/special-use TLDs like
# `.local`/`.internal`/`.test` as "not deliverable," which is exactly wrong
# for this project's target use case: an internal (사내) company tool, where
# `.local`/`.corp`/`.internal` email-style login IDs are common. This regex
# only checks basic structure, not real-world deliverability.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email_shape(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("must look like an email address (e.g. user@example.com or user@company.local)")
    return value


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""

    _check_email = field_validator("email")(_validate_email_shape)


class LoginRequest(BaseModel):
    email: str
    password: str

    _check_email = field_validator("email")(_validate_email_shape)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserOut
    access_token: str


def _issue(response: Response, user: models.User) -> AuthResponse:
    token = create_access_token(user.email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE)
    return AuthResponse(user=UserOut.model_validate(user), access_token=token)


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name or payload.email.split("@")[0],
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue(response, user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")
    return _issue(response, user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
