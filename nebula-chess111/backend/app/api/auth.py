from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator

from app.database import get_db
from app.models.user import User, RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.config import settings

router = APIRouter()

# FIX: timing-attack mitigation — verify_password is always called, even when
# the user does not exist, so response time cannot reveal username existence.
# Computed once at import time; cost is the same as a real hash check.
_DUMMY_HASH: str = hash_password("nebula-dummy-constant-for-timing-safety-xK9#")


# ── Request / response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email:    EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 32:
            raise ValueError("Username must be 3-32 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Only letters, numbers, _ and - allowed")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username_or_email: str
    password:          str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user_id:       str
    username:      str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db:   AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where(
            (User.username == body.username) | (User.email == body.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already registered")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    return await _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db:   AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(User).where(
            (User.username == body.username_or_email)
            | (User.email == body.username_or_email)
        )
    )
    user = q.scalar_one_or_none()

    # FIX: always run the bcrypt check — prevents timing-based username enumeration.
    # verify_password against _DUMMY_HASH takes the same time as a real check.
    candidate_hash = user.hashed_password if user else _DUMMY_HASH
    password_ok    = verify_password(body.password, candidate_hash)

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.is_banned:
        raise HTTPException(status_code=403, detail=f"Account banned: {user.ban_reason}")

    user.last_seen = datetime.now(timezone.utc)
    return await _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db:   AsyncSession = Depends(get_db),
):
    token_hash = hash_token(body.refresh_token)
    q = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked    == False,           # noqa: E712
            RefreshToken.expires_at >  datetime.now(timezone.utc),
        )
    )
    rt = q.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate: revoke old token, issue new pair
    rt.revoked = True
    user = await db.get(User, rt.user_id)
    if not user or not user.is_active or user.is_banned:
        raise HTTPException(status_code=403, detail="User not accessible")

    return await _issue_tokens(user, db)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    db:   AsyncSession = Depends(get_db),
):
    token_hash = hash_token(body.refresh_token)
    q  = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = q.scalar_one_or_none()
    if rt:
        rt.revoked = True


# ── Internal helper ───────────────────────────────────────────────────────────

async def _issue_tokens(user: User, db: AsyncSession) -> TokenResponse:
    access               = create_access_token(user.id, user.username)
    raw_refresh, hashed  = create_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hashed,
        expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    await db.flush()
    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        user_id=str(user.id),
        username=user.username,
    )
