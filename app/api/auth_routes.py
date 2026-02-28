"""Auth API — login, token refresh, current user."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    email: str
    role: str = "admin"


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Authenticate and return JWT."""
    if data.email != settings.admin_email:
        raise HTTPException(401, "Invalid credentials")
    if not verify_password(data.password, hash_password(settings.admin_password)):
        # For demo: compare plain text since we don't store hashed admin pw
        if data.password != settings.admin_password:
            raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": data.email, "role": "admin"})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserInfo(
        email=user.get("sub", ""),
        role=user.get("role", "user"),
    )
