"""
Auth router: /api/v1/auth
  POST /register  — create new user (admin only after first user)
  POST /token     — login with form data → tokens
  POST /refresh   — exchange refresh token → new access token
  GET  /me        — return current user profile
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.schemas import TokenRefreshRequest, TokenResponse, UserRegisterRequest, UserResponse
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.database.models import User, UserRole
from app.database.postgres import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user. The very first user is granted ADMIN role automatically.
    Subsequent registrations create AUDITOR accounts.
    """
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists.")

    # First user → admin
    count_result = await db.execute(select(User))
    is_first_user = count_result.first() is None

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.ADMIN if is_first_user else UserRole.AUDITOR,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 password flow login. Returns access + refresh tokens."""
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(require_auth)):
    """Return the currently authenticated user's profile."""
    return user
